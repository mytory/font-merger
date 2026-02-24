#!/usr/bin/env python3
import sys
import os
import argparse
import tempfile
from fontTools.merge import Merger
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.varLib.instancer import instantiateVariableFont

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
    # nameID 4: Full Name
    # nameID 6: PostScript Name
    family_name = new_name
    full_name = new_name
    ps_name = new_name.replace(" ", "-")

    for record in font['name'].names:
        if record.nameID == 1:
            record.string = family_name.encode(record.getEncoding())
        elif record.nameID == 4:
            record.string = full_name.encode(record.getEncoding())
        elif record.nameID == 6:
            record.string = ps_name.encode(record.getEncoding())


def format_weight_label(weight_value):
    if float(weight_value).is_integer():
        return str(int(weight_value))
    return f"{weight_value}".rstrip("0").rstrip(".")


def get_wght_axis(font):
    if "fvar" not in font:
        return None
    for axis in font["fvar"].axes:
        if axis.axisTag == "wght":
            return axis
    return None


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
    parser = argparse.ArgumentParser(description='Merge multiple fonts. Earlier fonts have higher priority.')
    parser.add_argument('--name', help='New font name')
    parser.add_argument('--weight', type=float, help="Weight value for variable fonts (wght axis)")
    parser.add_argument('fonts', nargs='+', help='Font files to merge (priority: first > last)')
    
    args = parser.parse_args()
    
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

    # 이름 설정 로직
    if not args.name:
        last_font_path = args.fonts[-1]
        base_name = get_font_family_name(last_font_path)
        args.name = f"Multilingual font based on {base_name}"

    if has_variable_font:
        weight_label = format_weight_label(args.weight)
        args.name = f"{args.name} W{weight_label}"
    
    print(f"[*] Target Font Name: {args.name}")
    print(f"[*] Priority Order: {' > '.join(args.fonts)}")
    if has_variable_font:
        print(f"[*] Variable font weight: {args.weight}")

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
