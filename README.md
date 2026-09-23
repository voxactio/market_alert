# 미국 VIX / 서킷브레이커 알림 봇 설정 가이드

매일 한국시간 08:00에 자동으로 실행되어, 지난 24시간 동안
- 미국 VIX 지수가 30 이상이었거나
- 미국 S&P500 지수가 전일 종가 대비 7% 이상 급락(서킷브레이커 수준)했다면
텔레그램으로 스마트폰 푸시 알림을 보내주는 프로그램입니다.

---

## 1단계. 텔레그램 봇 만들기

1. 스마트폰/PC에서 텔레그램 앱을 열고 **@BotFather** 를 검색해서 대화를 시작합니다.
2. `/newbot` 명령을 입력합니다.
3. 봇 이름과 아이디(예: `my_vix_alert_bot`)를 정해줍니다. (아이디는 반드시 `bot`으로 끝나야 함)
4. 완료되면 BotFather가 **토큰(TOKEN)** 을 알려줍니다. 예시:
   `123456789:AAExampleTokenStringHere`
   → 이 값을 메모해두세요. (이것이 `TELEGRAM_TOKEN` 입니다)
5. 방금 만든 봇을 텔레그램에서 검색해서 **아무 메시지나 하나** 보내주세요. (예: "안녕")
   → 봇이 나에게 메시지를 보내려면, 먼저 내가 봇과 대화를 한 번 시작해야 합니다.

## 2단계. 내 Chat ID 알아내기

1. 웹 브라우저 주소창에 아래 주소를 입력합니다 (TOKEN 부분을 본인 토큰으로 교체):
   ```
   https://api.telegram.org/bot<본인의 TOKEN>/getUpdates
   ```
2. 방금 봇에게 보낸 메시지 정보가 JSON 형태로 나옵니다. 그 안에서 아래처럼 생긴 숫자를 찾으세요:
   ```
   "chat":{"id":123456789, ...}
   ```
   → 이 숫자가 **`TELEGRAM_CHAT_ID`** 입니다.
3. 만약 결과가 비어있다면(`"result":[]`), 봇에게 메시지를 다시 보낸 뒤 새로고침 해보세요.

## 3단계. GitHub 저장소에 파일 올리기

1. [github.com](https://github.com) 에 가입/로그인 후, 새 저장소(Repository)를 만듭니다.
   (Public이든 Private이든 상관없습니다. Private을 추천합니다.)
2. 이 폴더 안의 파일들을 그대로 저장소에 업로드합니다. 구조는 다음과 같아야 합니다:
   ```
   your-repo/
   ├── market_alert.py
   ├── requirements.txt
   └── .github/
       └── workflows/
           └── market_alert.yml
   ```
   - GitHub 웹사이트에서 "Add file" → "Upload files"로 드래그해서 올려도 되고,
   - VS Code에서 Git 연동 후 push 해도 됩니다. (아래 "VS Code로 올리는 방법" 참고)

## 4단계. GitHub에 비밀 값(Secrets) 등록하기

토큰과 Chat ID는 코드에 직접 적지 않고 GitHub의 "Secrets" 기능에 안전하게 저장합니다.

1. 저장소 페이지 → **Settings** → 왼쪽 메뉴 **Secrets and variables** → **Actions** 클릭
2. **New repository secret** 버튼 클릭
3. 아래 2개를 각각 등록:
   - Name: `TELEGRAM_TOKEN` / Value: (1단계에서 받은 토큰)
   - Name: `TELEGRAM_CHAT_ID` / Value: (2단계에서 알아낸 숫자)

## 5단계. 자동 실행 확인하기

- `.github/workflows/market_alert.yml` 파일 덕분에 **매일 한국시간 08:00**에 자동 실행됩니다.
- 바로 테스트해보고 싶다면: 저장소 → **Actions** 탭 → **Market Alert (VIX / Circuit Breaker Check)** 클릭 →
  오른쪽의 **Run workflow** 버튼으로 즉시 수동 실행 가능합니다.
- 실행 로그는 Actions 탭에서 클릭해서 확인할 수 있습니다. (VIX 수치, 낙폭 % 등이 출력됩니다)

---

## VS Code로 올리는 방법 (파이썬/VS Code 이미 설치되어 있다는 가정)

1. 이 폴더를 VS Code로 엽니다. (File → Open Folder)
2. 왼쪽 "소스 제어(Source Control)" 아이콘 클릭 → "Initialize Repository" 클릭
3. GitHub에서 만든 저장소의 주소(예: `https://github.com/내아이디/저장소이름.git`)를 원격 저장소로 연결:
   - VS Code 하단 터미널(Terminal → New Terminal)에서 아래 명령 입력:
     ```
     git remote add origin https://github.com/내아이디/저장소이름.git
     git add .
     git commit -m "market alert bot"
     git branch -M main
     git push -u origin main
     ```
   - 처음 push 할 때 GitHub 로그인 창이 뜨면 로그인하면 됩니다.

## 로컬(내 PC)에서 미리 테스트해보기

터미널(VS Code 터미널도 가능)에서 순서대로 입력:

```bash
pip install -r requirements.txt

# Windows (PowerShell)
$env:TELEGRAM_TOKEN="본인토큰"
$env:TELEGRAM_CHAT_ID="본인챗아이디"
python market_alert.py

# Mac / Linux
export TELEGRAM_TOKEN="본인토큰"
export TELEGRAM_CHAT_ID="본인챗아이디"
python market_alert.py
```

조건이 충족되지 않아도 터미널에 VIX 수치와 낙폭 %가 출력되니, 정상 작동 여부를 바로 확인할 수 있습니다.

---

## 참고 및 한계

- **서킷브레이커 발동 여부**는 공식 발표를 실시간으로 크롤링하는 API가 없어서, S&P500 지수가 전일 종가 대비 7%/13%/20% 급락했는지를 대리 지표로 판단합니다. 실제 거래소 발표와 100% 일치하지 않을 수 있습니다.
- GitHub Actions의 무료 스케줄 실행은 서버가 바쁠 경우 몇 분 정도 지연될 수 있습니다 (보통 큰 문제는 없음).
- Public 저장소로 만들 경우 코드 자체는 공개되지만, Secrets 값(토큰/챗ID)은 외부에 노출되지 않습니다.
