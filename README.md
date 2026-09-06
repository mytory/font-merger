# font-merger

여러 폰트를 하나로 병합해 다국어 폰트를 만드는 CLI 도구입니다.

## GUI 다운로드

[GitHub Releases](../../releases/latest)에서 운영체제에 맞는 GUI 파일을 내려받을 수 있습니다.

- macOS (Apple Silicon): `font-merger-gui-macos-arm64.zip`을 압축 해제한 뒤 `Font Merger.app`을 응용 프로그램 폴더로 옮겨 실행합니다.
- macOS (Intel): `font-merger-gui-macos-x64.zip`을 압축 해제한 뒤 `Font Merger.app`을 응용 프로그램 폴더로 옮겨 실행합니다.
- Windows: `font-merger-gui-windows-x64.zip`을 압축 해제한 뒤 `font-merger-gui.exe`를 실행합니다.
- Linux: `font-merger-gui-linux-x64.tar.gz`을 압축 해제한 뒤 `font-merger-gui/font-merger-gui`를 실행합니다.

현재 배포물에는 코드 서명·공증이 적용되지 않았습니다. OS의 보안 경고가 나타날 수 있습니다.

- macOS: 앱을 열 수 없다는 경고가 나오면 **시스템 설정 → 개인정보 보호 및 보안 → 그래도 열기**를 선택합니다.
- Windows: SmartScreen 경고가 나오면 **추가 정보 → 실행**을 선택합니다.

배포물에 포함된 외부 라이브러리 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에서 확인할 수 있습니다.

## 요구사항

- Python 3
- `bash`

## 설치

```bash
./setup.sh
```

`setup.sh`는 다음을 수행합니다.

- `venv` 가상환경 생성
- `fonttools` 설치
- `PySide6` 설치 (GUI용)

## 사용법

```bash
./font-merger --name="New Font Name" font1.ttf font2.ttf font3.ttf
```

`--name`은 선택 사항입니다.

```bash
./font-merger font1.ttf font2.ttf font3.ttf
```

## GUI 사용법

```bash
./font-merger-gui
```

아이콘:

- 프로젝트 루트의 `icon.png`를 자동으로 읽어 창 아이콘으로 사용합니다.
- 별도 실행 옵션은 필요 없습니다.

GUI 기능:

- 폰트 파일 다중 선택 추가
- 폰트 파일 드래그 앤 드롭 추가
- 리스트 내부 드래그로 우선순위 순서 변경
- 이름, weight 입력
- auto-scale(기본 ON)
- 폰트별 수동 스케일 입력 (`N번 폰트는 1번 폰트의 [ ]% 크기`)
- 출력 폴더 선택
- 1회 병합 실행
- Variable 폰트가 포함된 경우에만 `Generate 100~900` 버튼 표시

스케일링 설명:

- 스케일링은 서로 다른 폰트의 글자 시각 크기를 맞추는 기능입니다.
- Auto scale은 1번 폰트를 기준으로 다른 폰트를 자동 보정합니다.
- 수동 스케일을 입력한 폰트는 해당 폰트에 한해 수동값이 Auto보다 우선합니다.
- 출력 폴더를 선택하지 않고 병합을 누르면 폴더 선택 창이 먼저 열립니다.
- 출력 폴더는 다음 실행에도 기억되며, 폴더가 사라진 경우 실행 시 자동으로 초기화됩니다.

## 데스크톱 실행파일 빌드

`PyInstaller`를 사용해 GUI 실행파일을 만들 수 있습니다.

```bash
source venv/bin/activate
pip install pyinstaller==6.17.0
```

```bash
# GUI 단일 실행파일
pyinstaller --noconfirm --windowed --onefile \
  --name font-merger-gui \
  --icon icon.png \
  --add-data "icon.png:." \
  font_merger_gui.py
```

Windows(cmd.exe)에서는 `--add-data` 구분자로 `;`를 사용합니다.

```bat
pyinstaller --noconfirm --windowed --onefile --name font-merger-gui --icon icon.png --add-data "icon.png;." font_merger_gui.py
```

빌드 결과:

- macOS/Linux: `dist/font-merger-gui`
- Windows: `dist/font-merger-gui.exe`

주의:

- 각 OS 실행파일은 해당 OS에서 빌드해야 합니다.
- 즉, macOS용은 macOS에서, Windows용은 Windows에서, Linux용은 Linux에서 빌드하세요.

가변 폰트(Variable Font)가 하나라도 포함되면 `--weight`가 필수입니다.

```bash
./font-merger --name="New Font Name" --weight=400 font1.ttf font2.ttf
```

글자 크기 보정을 위한 옵션:

```bash
# 자동 보정
./font-merger --weight=400 --auto-scale font1.ttf font2.ttf

# 수동 보정 (2번째 폰트 크기 93%)
./font-merger --weight=400 --scale-font2=0.93 font1.ttf font2.ttf
```

## 동작 규칙

- 우선순위: 앞에 입력한 폰트가 우선입니다.
- 즉, 글리프가 겹치면 `font1 > font2 > font3` 순으로 유지됩니다.
- 가변 폰트가 포함되면 `--weight` 값으로 `wght` 축을 고정한 뒤 병합합니다.
- `--name`을 주면 지정한 이름을 기준으로 사용합니다.
- `--auto-scale`을 사용하면 첫 번째 폰트를 기준으로 뒤 폰트의 시각적 크기를 자동 보정합니다.
- `--scale-fontN=<배율>`로 특정 입력 폰트 크기를 수동 보정할 수 있습니다. (`N`은 1부터 시작)
- `--scale-font1`은 허용되지 않습니다. 첫 번째 폰트는 기준 폰트입니다.
- `--auto-scale`과 `--scale-fontN`을 함께 쓰면 수동 보정값이 우선합니다.
- 가변 폰트가 포함되면 최종 이름 끝에 `W{weight}`가 자동으로 붙습니다.
- `--name`을 생략하면 첫 번째 폰트를 기준으로 자동 이름을 만듭니다.
  - 형식: `{first-font-name} Centered Merged Font`
- 출력 파일명은 `{폰트이름(공백은 _로 변경)} + {첫 번째 폰트의 확장자}` 입니다.

## 예시

```bash
./font-merger --name="My Multilingual Font" latin.ttf korean.ttf emoji.ttf
```

생성 파일 예:

`My_Multilingual_Font.ttf`

## 파일 구성

- `setup.sh`: 가상환경 및 의존성 설치
- `font-merger`: 실행용 래퍼 스크립트
- `_font_merger.py`: 병합 로직 본체
- `font-merger-gui`: GUI 실행용 래퍼 스크립트
- `font_merger_gui.py`: PySide6 GUI 앱
