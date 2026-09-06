## 윈도우에서 설치 방법

아래에서 `mytory-font-merger-windows-x64.zip` 파일을 다운받아 압축을 풀고 설치 파일을 더블클릭하면 보안 경고를 하는 빨간 창이 뜹니다(없애려면 비용을 내야 합니다). "추가 정보"를 클릭하고 실행하면 설치됩니다.

## 맥에서 설치 방법

아래에서 `mytory-font-merger-macos-arm64.zip`(m1 이후 맥)이나 `mytory-font-merger-macos-x64.zip`(구 인텔 맥)을 다운받아 압축을 풉니다.

압축을 풀면 나오는 `Mytory Font Merger.app` 파일을 우선 "응용 프로그램" 폴더로 옮기세요. 프로그램을 실행하면 아래처럼 보안 경고가 나옵니다(없애려면 비용을 내야 합니다). 휴지통으로 이동하지 말고 "완료"를 누르세요.

<img width="372" height="429" alt="보안 경고와 함께 휴지통으로 이동, 완료 두 버튼이 떠 있는 이미지" src="https://github.com/user-attachments/assets/e0c083b7-1057-4f8e-80ce-ac2f0bafdd6e" />

이 경고를 없애기 위해 "터미널" 앱을 열고 아래 명령어를 복사해 붙여 넣고 엔터를 칩니다.

```bash
sudo xattr -d com.apple.quarantine /Applications/Mytory\ Font\ Merger.app
```

아래 이미지를 참고하세요.

<img width="832" height="538" alt="터미널 앱에 명령어를 쳐넣는 모습. 검은 바탕에 위에 복붙하라고 한 명령어가 있고, 비밀번호 입력칸이 떠있다." src="https://github.com/user-attachments/assets/2061ee82-0eed-4475-bf13-8fbf49a2ff22" />

비밀번호를 입력하라고 나오면 입력을 하는데요, 입력을 해도 뭔가 입력되는 표시가 되지 않습니다. 안심하세요. 비밀번호라서 아예 아무것도 입력하지 않는 것처럼 보이는 것입니다. 비밀번호를 정확히 친 다음 엔터치면 됩니다.

아무 것도 출력되지 않으면 잘 된 것입니다. 이제 다시 실행해 보면 잘 되는 것을 볼 수 있습니다.
