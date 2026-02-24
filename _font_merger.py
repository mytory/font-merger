#!/usr/bin/env python3
import sys
import os
import argparse
import tempfile
import re
from datetime import datetime, UTC
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.boundsPen import BoundsPen

def get_font_family_name(font_path):
    """폰트 파일에서 Family Name을 추출합니다."""
    try:
        font = TTFont(font_path)
        # nameID 1: Family Name, nameID 4: Full Font Name
        # 우선순위: Full Name(4) -> Family Name(1) -> Filename
        names = font['name'].names
        for name_id in [4, 1]:
            for record in names:
                if record.nameID == name_id:
                    try:
                        return record.toUnicode()
                    except:
                        continue
    except Exception:
        pass
    return os.path.splitext(os.path.basename(font_path))[0]

def update_font_names(font, new_name):
    """병합된 폰트의 name 테이블을 새로운 이름으로 업데이트합니다."""
    # nameID 1: Family Name
    # nameID 2: Subfamily Name
    # nameID 3: Unique Font Identifier
    # nameID 4: Full Name
    # nameID 5: Version String
    # nameID 6: PostScript Name
    # nameID 16: Typographic Family Name
    # nameID 17: Typographic Subfamily Name
    # nameID 21/22: WWS Family/Subfamily Name
    # nameID 25: Variations PostScript Name Prefix
    family_name = new_name
    subfamily_name = "Regular"
    full_name = new_name
    ps_name = new_name.replace(" ", "-")
    version = "Version 1.000"
    unique_id = f"font-merger;{datetime.now(UTC).strftime('%Y%m%d%H%M%S')};{ps_name}"
    name_values = {
        1: family_name,
        2: subfamily_name,
        3: unique_id,
        4: full_name,
        5: version,
        6: ps_name,
        16: family_name,
        17: subfamily_name,
        21: family_name,
        22: subfamily_name,
        25: ps_name,
    }

    # Update existing records first (all languages/platforms)
    for record in font["name"].names:
        if record.nameID in name_values:
            value = name_values[record.nameID]
            try:
                record.string = value.encode(record.getEncoding(), errors="replace")
            except Exception:
                # Fallback for unusual encodings
                record.string = value.encode("utf-16-be")

    # Ensure required records exist for common platforms/locales
    for name_id, value in name_values.items():
        font["name"].setName(value, name_id, 3, 1, 0x409)  # Windows, Unicode, en-US
        font["name"].setName(value, name_id, 3, 1, 0x412)  # Windows, Unicode, ko-KR
        font["name"].setName(value, name_id, 1, 0, 0)      # Mac Roman, English


def format_weight_label(weight_value):
    if float(weight_value).is_integer():
        return str(int(weight_value))
    return f"{weight_value}".rstrip("0").rstrip(".")


def split_scale_args(argv):
    """Parse --scale-fontN options from argv and return (clean_argv, scale_map)."""
    clean = []
    scale_map = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        match_eq = re.match(r"^--scale-font(\d+)=(.+)$", token)
        match_sep = re.match(r"^--scale-font(\d+)$", token)
        if match_eq:
            font_index = int(match_eq.group(1))
            scale_map[font_index] = float(match_eq.group(2))
            i += 1
            continue
        if match_sep:
            font_index = int(match_sep.group(1))
            if i + 1 >= len(argv):
                raise ValueError(f"Missing value for {token}")
            scale_map[font_index] = float(argv[i + 1])
            i += 2
            continue
        clean.append(token)
        i += 1
    return clean, scale_map


def get_wght_axis(font):
    if "fvar" not in font:
        return None
    for axis in font["fvar"].axes:
        if axis.axisTag == "wght":
            return axis
    return None


def glyph_height(font, codepoint):
    cmap = font.getBestCmap() or {}
    glyph_name = cmap.get(codepoint)
    if glyph_name is None:
        return None
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    if pen.bounds is None:
        return None
    _, y_min, _, y_max = pen.bounds
    height = y_max - y_min
    if height <= 0:
        return None
    return height


def estimate_auto_scale(base_font_path, target_font_path):
    """Estimate scale ratio using shared representative glyph heights."""
    # Priority: Latin caps/x-height, then Hangul, then digits.
    candidates = [ord("H"), ord("x"), ord("A"), ord("a"), ord("가"), ord("한"), ord("0")]
    base = TTFont(base_font_path)
    target = TTFont(target_font_path)
    try:
        for cp in candidates:
            base_h = glyph_height(base, cp)
            target_h = glyph_height(target, cp)
            if base_h and target_h:
                return base_h / target_h, chr(cp)
    finally:
        base.close()
        target.close()
    return 1.0, None


def apply_visual_scale(font_path, index, temp_dir, scale_factor):
    if abs(scale_factor - 1.0) < 1e-6:
        return font_path
    font = TTFont(font_path)
    try:
        current_upem = font["head"].unitsPerEm
        scaled_upem = max(16, min(16384, int(round(current_upem * scale_factor))))
        if scaled_upem != current_upem:
            scale_upem(font, scaled_upem)
            # Keep the same UPEM so visual size is actually changed for merge.
            font["head"].unitsPerEm = current_upem
        ext = os.path.splitext(font_path)[1] or ".ttf"
        output_path = os.path.join(temp_dir, f"scaled_{index}{ext}")
        font.save(output_path)
        return output_path
    finally:
        font.close()


def prepare_font_for_merge(font_path, index, temp_dir, target_upem, weight_value):
    """병합 전처리: Variable Font static화 + unitsPerEm 정규화."""
    source_font = TTFont(font_path)
    try:
        work_font = source_font
        needs_save = False

        if "fvar" in source_font:
            axes = source_font["fvar"].axes
            axis_limits = {axis.axisTag: axis.defaultValue for axis in axes}
            wght_axis = get_wght_axis(source_font)
            if wght_axis is None:
                raise ValueError(f"Variable font has no 'wght' axis: {font_path}")
            if weight_value < wght_axis.minValue or weight_value > wght_axis.maxValue:
                raise ValueError(
                    f"--weight {weight_value} is out of range for {font_path} "
                    f"(allowed: {wght_axis.minValue}..{wght_axis.maxValue})"
                )
            axis_limits["wght"] = weight_value
            work_font = instantiateVariableFont(source_font, axis_limits, inplace=False)
            needs_save = True

        if "head" in work_font:
            current_upem = work_font["head"].unitsPerEm
            if current_upem != target_upem:
                scale_upem(work_font, target_upem)
                needs_save = True

        if not needs_save:
            return font_path

        ext = os.path.splitext(font_path)[1] or ".ttf"
        output_path = os.path.join(temp_dir, f"prepared_{index}{ext}")
        work_font.save(output_path)
        return output_path
    finally:
        source_font.close()
        if 'work_font' in locals() and work_font is not source_font:
            work_font.close()

def main():
    try:
        argv, scale_overrides = split_scale_args(sys.argv[1:])
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Merge multiple fonts. Earlier fonts have higher priority.')
    parser.add_argument('--name', help='New font name')
    parser.add_argument('--weight', type=float, help="Weight value for variable fonts (wght axis)")
    parser.add_argument('--auto-scale', action='store_true', help='Auto-scale non-first fonts to match first font size')
    parser.add_argument('fonts', nargs='+', help='Font files to merge (priority: first > last)')
    
    args = parser.parse_args(argv)
    
    if not args.fonts:
        print("Error: No font files provided.")
        sys.exit(1)

    has_variable_font = False
    for font_path in args.fonts:
        font = TTFont(font_path)
        try:
            if "fvar" in font:
                has_variable_font = True
                break
        finally:
            font.close()

    if has_variable_font and args.weight is None:
        print("Error: --weight is required when input includes variable fonts.")
        sys.exit(1)

    for font_idx, scale_value in scale_overrides.items():
        if font_idx < 1 or font_idx > len(args.fonts):
            print(f"Error: --scale-font{font_idx} is out of range (fonts count: {len(args.fonts)}).")
            sys.exit(1)
        if font_idx == 1:
            print("Error: --scale-font1 is not allowed. The first font is the reference font.")
            sys.exit(1)
        if scale_value <= 0:
            print(f"Error: --scale-font{font_idx} must be > 0.")
            sys.exit(1)

    # 이름 설정 로직 (첫 번째 폰트 기준)
    if not args.name:
        first_font_path = args.fonts[0]
        base_name = get_font_family_name(first_font_path)
        args.name = f"{base_name} Centered Merged Font"

    if has_variable_font:
        weight_label = format_weight_label(args.weight)
        args.name = f"{args.name} W{weight_label}"
    
    print(f"[*] Target Font Name: {args.name}")
    print(f"[*] Reference Font (font1): {args.fonts[0]}")
    print(f"[*] Overwrite Priority: {' > '.join(args.fonts)}")
    if has_variable_font:
        print(f"[*] Variable font weight: {args.weight}")
    if scale_overrides:
        print(f"[*] Manual scales: {scale_overrides}")
    if args.auto_scale:
        print("[*] Auto scale: enabled")

    # Merger 초기화 및 실행
    # fontTools.merge.Merger는 리스트의 앞에 있는 폰트를 우선시합니다.
    merger = Merger()
    
    print("[*] Merging...")
    try:
        with tempfile.TemporaryDirectory(prefix="font-merger-") as temp_dir:
            first_font = TTFont(args.fonts[0])
            try:
                target_upem = first_font["head"].unitsPerEm
            finally:
                first_font.close()

            prepared_fonts = [
                prepare_font_for_merge(path, i, temp_dir, target_upem, args.weight)
                for i, path in enumerate(args.fonts)
            ]

            base_font_path = prepared_fonts[0]
            for i in range(1, len(prepared_fonts)):
                manual_scale = scale_overrides.get(i + 1)
                auto_scale = 1.0
                char_used = None
                if manual_scale is None and args.auto_scale:
                    auto_scale, char_used = estimate_auto_scale(base_font_path, prepared_fonts[i])
                    # Keep auto-scale in a conservative range.
                    auto_scale = max(0.5, min(2.0, auto_scale))

                scale_factor = manual_scale if manual_scale is not None else auto_scale
                if manual_scale is not None or args.auto_scale:
                    label = f"manual({manual_scale})" if manual_scale is not None else f"auto({auto_scale:.4f})"
                    if char_used:
                        label += f" via '{char_used}'"
                    print(f"[*] Scale font{i+1}: {label}")
                prepared_fonts[i] = apply_visual_scale(prepared_fonts[i], i, temp_dir, scale_factor)

            merged_font = merger.merge(prepared_fonts)
        
        # 이름 업데이트
        update_font_names(merged_font, args.name)
        
        # 저장 (확장자는 첫 번째 폰트를 따름)
        ext = os.path.splitext(args.fonts[0])[1]
        output_filename = f"{args.name.replace(' ', '_')}{ext}"
        
        merged_font.save(output_filename)
        print(f"[+] Success! Saved to: {output_filename}")
        
    except Exception as e:
        print(f"[-] Error during merge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
