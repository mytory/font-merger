# font-merger

여러 폰트를 하나로 병합해 다국어 폰트를 만드는 CLI 도구입니다.

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

GUI 기능:

- 폰트 파일 추가/삭제/순서 변경
- 이름, weight, auto-scale, manual scale 입력
- 1회 병합 실행
- Variable 폰트가 포함된 경우에만 `Generate 100~900` 버튼 표시

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
