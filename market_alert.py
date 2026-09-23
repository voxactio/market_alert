"""
[매일 체크] 08:00 KST(한국시간) 기준으로 최근 24시간 동안
1) 미국 VIX 지수가 30 이상이었는지
2) 미국 S&P500 지수가 전일 종가 대비 7% 이상 급락(서킷브레이커 수준)했는지
를 확인해서, 조건에 해당하면 텔레그램으로 알림을 보내는 스크립트.

[매월 테스트] 매월 1일 09:00 KST에는 조건 충족 여부와 상관없이
- VIX 지수
- S&P500 전일 종가 / 당일 종가
- 전일 대비 당일 증감률
을 무조건 텔레그램으로 보내서, 시스템이 잘 작동하는지 확인할 수 있게 합니다.

주의: "서킷브레이커가 실제로 발동됐는지"를 알려주는 공식 API는 없기 때문에,
S&P500(^GSPC) 지수의 급락폭(7%/13%/20%)을 대리 지표로 사용합니다.
"""

import os
import sys
import datetime
import requests
import yfinance as yf

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

VIX_THRESHOLD = 30.0
CIRCUIT_BREAKER_LEVELS = [
    (20.0, "3단계 (거래 전면 중단 수준)"),
    (13.0, "2단계"),
    (7.0, "1단계"),
]

# GitHub Actions 워크플로우의 매월 테스트용 cron 표현식과 동일해야 함
MONTHLY_TEST_CRON = "0 0 1 * *"


def send_telegram(message: str) -> None:
    """텔레그램 봇으로 메시지를 보낸다."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 TOKEN/CHAT_ID가 설정되지 않았습니다. 환경변수를 확인하세요.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
    resp.raise_for_status()


def check_vix():
    """최근 VIX 종가를 확인. (VIX 값, 30 이상 여부) 반환."""
    vix = yf.Ticker("^VIX")
    hist = vix.history(period="5d", interval="1d")
    if hist.empty:
        print("VIX 데이터를 가져오지 못했습니다.")
        return None, False

    latest_close = float(hist["Close"].iloc[-1])
    triggered = latest_close >= VIX_THRESHOLD
    return latest_close, triggered


def check_circuit_breaker():
    """
    최근 24시간(장중 15분봉) 동안의 최저가를 전일 종가와 비교해
    급락폭(%)을 계산하고, 서킷브레이커 발동 가능 수준인지 확인한다.
    """
    sp500 = yf.Ticker("^GSPC")

    daily = sp500.history(period="10d", interval="1d")
    if len(daily) < 2:
        print("S&P500 일봉 데이터를 충분히 가져오지 못했습니다.")
        return False, None, None

    prev_close = float(daily["Close"].iloc[-2])

    intraday = sp500.history(period="5d", interval="15m")
    if intraday.empty:
        print("S&P500 분봉 데이터를 가져오지 못했습니다.")
        return False, None, None

    intraday = intraday.sort_index()
    cutoff = intraday.index[-1] - datetime.timedelta(hours=24)
    recent = intraday[intraday.index >= cutoff]
    if recent.empty:
        recent = intraday

    min_price = float(recent["Low"].min())
    drop_pct = (prev_close - min_price) / prev_close * 100

    triggered = False
    level_label = None
    for threshold, label in CIRCUIT_BREAKER_LEVELS:
        if drop_pct >= threshold:
            triggered = True
            level_label = label
            break

    return triggered, drop_pct, level_label


def get_sp500_two_closes():
    """S&P500의 최근 두 거래일 종가(전일, 당일)와 증감률(%)을 반환한다."""
    sp500 = yf.Ticker("^GSPC")
    daily = sp500.history(period="10d", interval="1d")
    if len(daily) < 2:
        return None, None, None

    prev_close = float(daily["Close"].iloc[-2])
    latest_close = float(daily["Close"].iloc[-1])
    change_pct = (latest_close - prev_close) / prev_close * 100
    return prev_close, latest_close, change_pct


def send_monthly_test_report():
    """매월 1일 09:00 KST에 조건과 상관없이 현재 지표를 요약해서 보낸다."""
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)

    vix_value, _ = check_vix()
    prev_close, latest_close, change_pct = get_sp500_two_closes()

    lines = [
        "📊 [테스트 알림] 시장 지표 정기 점검",
        f"(발송 시각: {now_kst.strftime('%Y-%m-%d %H:%M')} KST)",
        "",
    ]

    if vix_value is not None:
        lines.append(f"• VIX 지수: {vix_value:.2f}")
    else:
        lines.append("• VIX 지수: 조회 실패")

    if prev_close is not None:
        sign = "+" if change_pct >= 0 else ""
        lines.append(f"• S&P500 전일 종가: {prev_close:,.2f}")
        lines.append(f"• S&P500 당일 종가: {latest_close:,.2f}")
        lines.append(f"• 전일 대비 증감률: {sign}{change_pct:.2f}%")
    else:
        lines.append("• S&P500 종가: 조회 실패")

    lines += ["", "(이 알림은 시스템이 정상 작동 중인지 확인하기 위한 월간 테스트입니다.)"]

    message = "\n".join(lines)
    send_telegram(message)
    print("월간 테스트 알림을 발송했습니다.")
    print(message)


def main():
    trigger_cron = os.environ.get("TRIGGER_CRON", "")
    manual_mode = os.environ.get("MANUAL_MODE", "")

    if trigger_cron == MONTHLY_TEST_CRON or manual_mode == "monthly_test":
        send_monthly_test_report()
        return

    _run_daily_check()


def _run_daily_check():
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    print(f"체크 시각(KST): {now_kst.strftime('%Y-%m-%d %H:%M')}")

    vix_value, vix_triggered = check_vix()
    cb_triggered, drop_pct, level_label = check_circuit_breaker()

    print(f"VIX: {vix_value} / 30 이상 여부: {vix_triggered}")
    if drop_pct is not None:
        print(f"S&P500 최대 낙폭: {drop_pct:.2f}% / 서킷브레이커 조건 여부: {cb_triggered}")

    if vix_triggered or cb_triggered:
        lines = ["⚠️ 미국 증시 경고 알림", f"(확인 시각: {now_kst.strftime('%Y-%m-%d %H:%M')} KST)", ""]
        if vix_triggered:
            lines.append(f"• VIX 지수 {vix_value:.2f} (기준 30 이상 충족)")
        if cb_triggered:
            lines.append(f"• S&P500 낙폭 {drop_pct:.2f}% → 서킷브레이커 {level_label} 조건 충족 가능")
        message = "\n".join(lines)
        send_telegram(message)
        print("텔레그램 알림을 발송했습니다.")
    else:
        print("조건 미충족. 알림을 보내지 않습니다.")


if __name__ == "__main__":
    main()
