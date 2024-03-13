

import datetime
import json
import numpy as np
import pandas as pd
import requests
import streamlit as st
import time
import websocket  # websocket-client

# from upbit_logics import get_all_tickers_candles

###############################################################################
# 공통
###############################################################################

########## 업비트 API 관련 ##########
@st.cache_data
def get_all_tickers_from_upbit():

    # get all tickers from Upbit
    query_market_tickers_url = "https://api.upbit.com/v1/market/all"
    response = requests.get(query_market_tickers_url)
    data = response.json()
    tickers = [d["market"] for d in data if d["market"].startswith("KRW-")]
    return tickers

########## ticker checkbox 관련 ##########
def check_all_tickers():
    for key in st.session_state:
        if key.endswith("_ticker_checkbox"):
            st.session_state[key] = True
    return

def uncheck_all_tickers(): 
    for key in st.session_state:
        if key.endswith("_ticker_checkbox"):
            st.session_state[key] = False
    return

########## BOOK read/write 관련 ##########
def load_BOOK_data():
    global BOOK
    try:
        with open(BOOK_PATH, 'r', encoding="utf8") as f:
            BOOK = json.load(f)
            print("past ohlcpv log loaded")
    except:
        print("No past ohlcpv log file. pass")
    return

def save_BOOK_data():
    global BOOK
    with open(BOOK_PATH, 'w', encoding="utf8") as f:
        json.dump(BOOK, f)
    return


# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================

BOOK = {}
BOOK_PATH = "book.json"


###############################################################################
# Upbit Query
###############################################################################

def update_ohlcpvs(tickers, units):

    global BOOK

    # BOOK 내용 불러오기
    load_BOOK_data()

    # 조회할 마켓 목록 생성
    targets = [f"{ticker},{unit}" for ticker in tickers for unit in units]

    # query block 방지용 시간 체크용 쿼리 요청 시간 목록
    query_times = []

    # target 별 ohlcpv API 요청
    for i, target in enumerate(targets):
        ticker, unit = target.split(",")

        # ohlcpv 업데이트 해야하는지 확인       // 어짜피 마지막 거래가는 계속 변하므로 무조건 호출. 임시 주석처리
        # update_needed = need_to_update_ohlcpv(target)
        update_needed = True

        # 업데이트 중 메세지 출력 
        message = f"Request OHLCPV from Upbit - {i+1: 3d} / {len(targets)}. Working on : {target:20s}" + "" if update_needed else "  cached"
        print(message); ohlcpv_message_area.text(message)
        if not update_needed: continue

        # query block 방지용 시간 체크. 1초이내 9개 도달하면 1초 쉼. (업비트 문서 기준 최대 초당 10개, 버퍼 1개)
        now = time.time()
        query_times.append(now)
        query_times = [qt for qt in query_times if now - qt <= 1]  # 지난 1초 이내 쿼리 목록
        if len(query_times) >= 9: time.sleep(1); 

        # request ohlcpv data
        unit_text_to_unit = {"months": "months", "weeks": "weeks", "days":"days", "240분":"minutes/240", "60분":"minutes/60", "30분":"minutes/30",
                             "15분":"minutes/15", "10분":"minutes/10", "5분":"minutes/5", "3분":"minutes/3", "1분":"minutes/1"}
        url = f"https://api.upbit.com/v1/candles/{unit_text_to_unit[unit]}?market={ticker}&count=200"
        ohlcpv = candles_to_ohlcpv(requests.get(url).json())

        # 저장
        if target not in BOOK: BOOK[target] = {}
        for key2 in ohlcpv:
            BOOK[target][key2] = ohlcpv[key2]
            BOOK[target]["last_ohlcpv_update_time"] = time.time()


    # 업데이트 완료 메세지 출력
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["ohlcpv_update_message"] = f"Request OHLCPV from Upbit - 업데이트 완료 ( {now} )"
    ohlcpv_message_area.text(st.session_state["ohlcpv_update_message"])

    # BOOK 내용 저장
    save_BOOK_data()
   
    return

def set_targets():

    # ohlcpv 업데이트할 query targets 범위 설정
    # units = ["days", "240", "60", "15"]
    units = ["60"]

    # get all tickers from Upbit
    query_market_tickers_url = "https://api.upbit.com/v1/market/all"
    response = requests.get(query_market_tickers_url)
    data = response.json()
    tickers = [d["market"] for d in data if d["market"].startswith("KRW-")]
    
    # build targets
    targets = [(ticker, unit) for ticker in tickers for unit in units]

    return targets

def need_to_update_ohlcpv(key):

    ticker, unit = key.split(',')

    now = time.time()
    try:
        if key not in BOOK: return True
        if unit == "months":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 2592000:  # 30 days
                return True
            return False
        if unit == "weeks":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 604800:  # 7 days
                return True
            return False
        if unit == "days":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 86400:  # 1 day
                return True
            return False
        if unit == "240":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 14400: # 4 hours
                return True
            return False
        if unit == "60":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 3600: # 1 hour
                return True
            return False
        if unit == "30":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 1800: # 30 minutes
                return True
            return False
        if unit == "15":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 900: # 15 minutes
                return True
            return False
        if unit == "10":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 600: # 10 minutes
                return True
            return False
        if unit == "5":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 300: # 5 minutes
                return True
            return False
        if unit == "3":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 180: # 3 minutes
                return True
            return False
        if unit == "1":
            if now - BOOK[key]["last_ohlcpv_update_time"] > 60: # 1 minute
                return True
            return False
    except:         # 삐꾸나면 업뎃하셈
        return True
    
def candles_to_ohlcpv(candles):

    date_time_ksts = []
    opens = []
    highs = []
    lows  = []
    trades = []
    tot_prices = []
    tot_volumes = []

    for candle in candles:

        candle_date_time_utc = candle["candle_date_time_utc"]
        candle_date_time_kst = candle["candle_date_time_kst"]
        opening_price = candle["opening_price"]
        high_price = candle["high_price"]
        low_price = candle["low_price"]
        trade_price = candle["trade_price"]
        candle_acc_trade_price = candle["candle_acc_trade_price"]
        candle_acc_trade_volume = candle["candle_acc_trade_volume"]

        date_time_ksts.append(candle_date_time_kst)
        opens.append(opening_price)
        highs.append(high_price)
        lows.append(low_price)
        trades.append(trade_price)
        tot_prices.append(candle_acc_trade_price)
        tot_volumes.append(candle_acc_trade_volume)

    ohlcpv = {}
    ohlcpv["date_time_ksts"] = date_time_ksts
    ohlcpv["opens"] = opens
    ohlcpv["highs"] = highs
    ohlcpv["lows"] = lows
    ohlcpv["trades"] = trades
    ohlcpv["tot_prices"] = tot_prices
    ohlcpv["tot_volumes"] = tot_volumes

    return ohlcpv


###############################################################################
# Indicators
###############################################################################

def update_indicators(tickers, units):

    global BOOK

    # BOOK 내용 불러오기
    load_BOOK_data()

    # 보조지표를 계산할 마켓 목록 생성
    targets = [f"{ticker},{unit}" for ticker in tickers for unit in units]

    # target 별 보조지표 계산
    for i, target in enumerate(targets):
        ticker, unit = target.split(",")
        
        # 업데이트 중 메세지 출력
        message = f"Calculate Indicators \t  -\t{i+1: 3d} / {len(targets)} working on : {target:20s}"
        print(message); indicators_message_area.text(message)

        dt_ksts = BOOK[target]["date_time_ksts"]
        opens = BOOK[target]["opens"]
        highs = BOOK[target]["highs"]
        lows = BOOK[target]["lows"]
        trades = BOOK[target]["trades"]
        tot_prices = BOOK[target]["tot_prices"]
        tot_volumes = BOOK[target]["tot_volumes"]

        # RSI
        RSIs = get_RSIs(trades)
        BOOK[target]["RSI"] = RSIs

        # MACD
        MACDs, MACD_signals = get_MACDs(trades)
        BOOK[target]["MACD"] = MACDs
        BOOK[target]["MACD_signal"] = MACD_signals

        # Williams %R
        WilliamsRs = get_WilliamsR(highs, lows, trades)
        BOOK[target]["Williams%R"] = WilliamsRs

    # 업데이트 완료 메세지 출력
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["indicators_update_message"] = f"Calculate Indicators \t  - 업데이트 완료 ( {now} )"
    indicators_message_area.text(st.session_state["indicators_update_message"])

    # BOOK 내용 저장
    save_BOOK_data()

    return

def get_RSIs(closes, period=14):

    # 현재과거 순에서 과거현재 순으로 뒤집기 (계산용)
    closes = closes[::-1]

    # 1
    differences = []
    for i in range(len(closes) - 1):
        differences.append(closes[i+1] - closes[i])

    # 2
    U = [u if u > 0 else 0 for u in differences]
    D = [-d if d < 0 else 0 for d in differences]

    # 3
    EWM_U = ewm(U, period, a_type="com", adjust=False)
    EWM_D = ewm(D, period, a_type="com", adjust=False)

    # 4
    RSs = []
    for i in range(len(EWM_U)):
        if EWM_U[i] is None or EWM_D[i] is None or EWM_D[i] == 0:
            RSs.append(None)
        else:
            RSs.append(EWM_U[i] / EWM_D[i])

    # 5
    RSIs = []
    for i in range(len(RSs)):
        if RSs[i] is None:
            RSIs.append(None)
        else:
            RSIs.append(100 - (100 / (1 + RSs[i])))

    return RSIs[::-1]

def get_MACDs(closes, period1=12, period2=26, period3=9):

    # 현재과거 순에서 과거현재 순으로 뒤집기 (계산용)
    closes = closes[::-1]

    EWM12 = ewm(closes, period1, a_type="span", adjust=False)
    EWM26 = ewm(closes, period2, a_type="span", adjust=False)

    MACDs = [EWM12[i] - EWM26[i] for i in range(len(EWM12))]
    MACD_signals = ewm(MACDs, period3, a_type="span", adjust=False)

    return MACDs[::-1], MACD_signals[::-1]

def get_WilliamsR(highs, lows, closes, period=14):

    highs  = highs[::-1]
    lows   = lows[::-1]
    closes = closes[::-1]

    high_highs = [max(highs[max(0, i-period):i+1]) for i in range(len(highs))]
    low_lows   = [min(lows[max(0, i-period):i+1]) for i in range(len(lows))]
    
    williamsRs = []
    for i, close in enumerate(closes):
        williamsRs.append((high_highs[i] - close) / (high_highs[i] - low_lows[i]) * -100)

    return williamsRs[::-1]

def ewm(data, period, a_type="span", adjust=True):

    if a_type == "span":

        if adjust:

            EWM_a = 2 / (1 + period)
            EWMs = [None] * (period - 1)
            for i in range(len(data) - period + 1):
                data_frame = data[i:i+period]
                ewm = 0
                ewm = data_frame[0]
                for d in data_frame[1:]:
                    ewm = d * EWM_a + ewm * (1 - EWM_a)
                EWMs.append(ewm)
            return EWMs
        else:
            
            EWM_a = 2 / (1 + period)
            EWMs = [data[0]]
            for d in data[1:]:
                EWMs.append(d * EWM_a + EWMs[-1] * (1 - EWM_a))
            return EWMs
        
    if a_type == "com":

        if adjust:
            EWM_a = 1 / (1 + (period - 1))
            EWMs = [None] * (period - 1)
            for i in range(len(data) - period + 1):
                data_frame = data[i:i+period]
                ewm = data_frame[0]
                for d in data_frame[1:]:
                    ewm = d * EWM_a + ewm * (1 - EWM_a)
                EWMs.append(ewm)
            return EWMs
        else:
            EWM_a = 1 / (1 + (period - 1))
            EWMs = [data[0]]
            for d in data[1:]:
                EWMs.append(d * EWM_a + EWMs[-1] * (1 - EWM_a))
            return EWMs

    return


###############################################################################
# Filter (Evaluate)
###############################################################################

def update_evaluations(tickers, units):

    global BOOK

    # BOOK 내용 불러오기
    load_BOOK_data()

    # 평가할 마켓 목록 생성
    targets = [f"{ticker},{unit}" for ticker in tickers for unit in units]

    for i, target in enumerate(targets):
        ticker, unit = target.split(",")
        
        # 업데이트 중 메세지 출력
        message = f"Evaluate status \t  -\t{i+1: 3d} / {len(targets)} working on : {target:20s}"
        print(message); evaluations_message_area.text(message)

        if "eval" not in BOOK[target]: BOOK[target]["eval"] = {}

        RSIs = BOOK[target]["RSI"]
        RSI_status = get_RSI_status(RSIs)
        BOOK[target]["eval"]["RSI"] = RSI_status

        MACDs = BOOK[target]["MACD"]
        MACD_signals = BOOK[target]["MACD_signal"]
        MACD_status = get_MACD_status(MACDs, MACD_signals)
        BOOK[target]["eval"]["MACD"] = MACD_status

        WilliamsRs = BOOK[target]["Williams%R"]
        WilliamsR_status = get_WilliamsR_status(WilliamsRs)
        BOOK[target]["eval"]["Williams%R"] = WilliamsR_status

    # 업데이트 완료 메세지 출력
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["evaluations_update_message"] = f"Evaluate status \t  - 업데이트 완료 ( {now} )"
    evaluations_message_area.text(st.session_state["evaluations_update_message"])

    # BOOK 내용 저장
    save_BOOK_data()

    return

def get_RSI_status(RSIs):

    high_line = 70
    low_line  = 30

    # 과매도 상향돌파
    cur_RSI_over_low_line = RSIs[0] > low_line
    l1_RSI_under_low_line = RSIs[1] < low_line
    l2_RSi_under_low_line = RSIs[2] < low_line
    if cur_RSI_over_low_line and l1_RSI_under_low_line and l2_RSi_under_low_line:
        return "과매도 상향돌파"
    
    # 과매도 상향돌파 임박
    delta = RSIs[0] - RSIs[1]
    n1_RSI_over_low_line = RSIs[0] + delta > low_line
    cur_RSI_under_low_line = RSIs[0] < low_line
    l1_RSI_under_low_line = RSIs[1] < low_line
    if n1_RSI_over_low_line and cur_RSI_under_low_line and l1_RSI_under_low_line:
        return "과매도 상향돌파 임박"

    # 과매수 하향돌파
    cur_RSI_under_high_line = RSIs[0] < high_line
    l1_RSI_over_high_line = RSIs[1] > high_line
    l2_RSI_over_high_line = RSIs[2] > high_line
    if cur_RSI_under_high_line and l1_RSI_over_high_line and l2_RSI_over_high_line:
        return "과매수 하향돌파"
    
    # 과매수 하향돌파 임박
    delta = RSIs[0] - RSIs[1]
    n1_RSI_under_high_line = RSIs[0] + delta < high_line
    cur_RSI_over_high_line = RSIs[0] > high_line
    l1_RSI_over_high_line = RSIs[1] > high_line
    if n1_RSI_under_high_line and cur_RSI_over_high_line and l1_RSI_over_high_line:
        return "과매수 하향돌파 임박"
    
    return "별일 없음"

def get_MACD_status(MACDs, MACD_signals):

    # 골든크로스
    cur_MACD_over_signal = MACDs[0] > MACD_signals[0]
    l1_MACD_under_signal = MACDs[1] < MACD_signals[1]
    l2_MACD_under_signal = MACDs[2] < MACD_signals[2]
    if cur_MACD_over_signal and l1_MACD_under_signal and l2_MACD_under_signal:
        return "골든크로스"

    # 골든크로스 임박
    MACD_delta = MACDs[0] - MACDs[1]
    MACD_signal_delta = MACD_signals[0] - MACD_signals[1]
    n1_MACD_over_signal = MACDs[0] + MACD_delta > MACD_signals[0] + MACD_signal_delta
    cur_MACD_under_signal = MACDs[0] < MACD_signals[0]
    l1_MACD_under_signal = MACDs[1] < MACD_signals[1]
    if n1_MACD_over_signal and cur_MACD_under_signal and l1_MACD_under_signal:
        return "골든크로스 임박"
    
    # 데드크로스
    cur_MACD_under_signal = MACDs[0] < MACD_signals[0]
    l1_MACD_over_signal = MACDs[1] > MACD_signals[1]
    l2_MACD_over_signal = MACDs[2] > MACD_signals[2]
    if cur_MACD_under_signal and l1_MACD_over_signal and l2_MACD_over_signal:
        return "데드크로스"
    
    # 데드크로스 임박
    MACD_delta = MACDs[0] - MACDs[1]
    MACD_signal_delta = MACD_signals[0] - MACD_signals[1]
    n1_MACD_under_signal = MACDs[0] + MACD_delta < MACD_signals[0] + MACD_signal_delta
    cur_MACD_over_signal = MACDs[0] > MACD_signals[0]
    l1_MACD_over_signal = MACDs[1] > MACD_signals[1]
    if n1_MACD_under_signal and cur_MACD_over_signal and l1_MACD_over_signal:
        return "데드크로스 임박"

    return "별일 없음"

def get_WilliamsR_status(WilliamsRs):

    high_line = -20
    low_line  = -80

    # 과매도 상향돌파
    cur_W_over_low_line = WilliamsRs[0] > low_line
    l1_W_under_low_line = WilliamsRs[1] < low_line
    l2_W_under_low_line = WilliamsRs[2] < low_line
    if cur_W_over_low_line and l1_W_under_low_line and l2_W_under_low_line:
        return "과매도 상향돌파"

    # 과매도 상향돌파 임박
    W_delta = WilliamsRs[0] - WilliamsRs[1]
    n1_W_over_low_line = WilliamsRs[0] + W_delta > low_line
    cur_W_under_low_line = WilliamsRs[0] < low_line
    l1_W_under_low_line = WilliamsRs[1] < low_line
    if n1_W_over_low_line and cur_W_under_low_line and l1_W_under_low_line:
        return "과매도 상향돌파 임박"
    
    # 과매수 하향돌파
    cur_W_under_high_line = WilliamsRs[0] < high_line
    l1_W_over_high_line = WilliamsRs[1] > high_line
    l2_W_over_high_line = WilliamsRs[2] > high_line
    if cur_W_under_high_line and l1_W_over_high_line and l2_W_over_high_line:
        return "과매수 하향돌파"
    
    # 과매수 하향돌파 임박
    W_delta = WilliamsRs[0] - WilliamsRs[1]
    n1_W_under_high_line = WilliamsRs[0] + W_delta < high_line
    cur_W_over_high_line = WilliamsRs[0] > high_line
    l1_W_over_high_line = WilliamsRs[1] > high_line
    if n1_W_under_high_line and cur_W_over_high_line and l1_W_over_high_line:
        return "과매수 하향돌파 임박"

    return "별일 없음"


###############################################################################
# Volume Power
###############################################################################


def update_volume_powers(tickers, units):

    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####
    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####
    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####
    def on_message(ws, message):
        # do something
        msg_recieved = message.decode('utf-8')
        data = json.loads(msg_recieved)
        code = data["code"]
        recieved[code] = data

        if len(tickers) == len(recieved):

            ws_app.close()

    def on_connect(ws):
        print("connected!")
        data_to_send = [{"ticket": "jyjyrequestforvp91826642"},
            {"type": "ticker", "codes": tickers, "isOnlySnapshot": True},
            {"format": "DEFAULT"}
            ]
        message = json.dumps(data_to_send)
        ws.send(message)

    def on_error(ws, err):
        print(err)

    def on_close(ws, status_code, msg):
        print("closed!")
    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####
    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####
    ###### for websocket ##### ###### for websocket ##### ###### for websocket #####

    global BOOK

    # BOOK 내용 불러오기
    load_BOOK_data()

    # web socket url
    recieved = {}
    ws_app = websocket.WebSocketApp("wss://api.upbit.com/websocket/v1", on_open=on_connect)
    ws_app.on_message = on_message
    ws_app.run_forever()
    max_retries = 100
    count = 0
    while len(recieved) < len(tickers):
        if count > max_retries: break
        count += 1
        time.sleep(0.2)
    ws_app.close()

    # 마켓 목록 생성
    targets = [f"{ticker},{unit}" for ticker in tickers for unit in units]

    for i, target in enumerate(targets):
        ticker, unit = target.split(",")
        
        # 업데이트 중 메세지 출력
        message = f"Volume Power Query status -\t{i+1: 3d} / {len(targets)} working on : {target:20s}"
        print(message); volume_powers_message_area.text(message)

        # 정보
        data = recieved[ticker]

        acc_bid_volume = data["acc_bid_volume"]  # UTC 00:00 이후 물량
        acc_ask_volume = data["acc_ask_volume"]  # UTC 00:00 이후 물량
        volume_power = f"{round(acc_bid_volume / acc_ask_volume * 100, 2):.2f}"
        BOOK[target]["volume_power"] = volume_power

    # 업데이트 완료 메세지 출력
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["volume_powers_update_message"] = f"Volume Power Query status - 업데이트 완료 ( {now} )"
    volume_powers_message_area.text(st.session_state["volume_powers_update_message"])

    # BOOK 내용 저장
    save_BOOK_data()

    return


###############################################################################
# Page Layout
###############################################################################

st.set_page_config(layout="wide")

#####
# 제목 영역
#####
st.title('sasdf')


##############################
# 조회 Ticker 선택 영역
##############################
ticker_list_column_size = 6

with st.expander("업데이트할 Ticker 선택"):
    # 전체 선택 / 해제
    tickers_button_container = st.container()
    button_row = tickers_button_container.columns(6)
    with button_row[0]: st.button("전체 선택", on_click=check_all_tickers)
    with button_row[1]: st.button("전체 해제", on_click=uncheck_all_tickers)
    ticker_list = st.container(height=200)

    # upbit ticker 전부 가져와서 영역 checkbox row, column 생성
    upbit_tickers = get_all_tickers_from_upbit()
    l = []
    list_size = len(upbit_tickers) // ticker_list_column_size if len(upbit_tickers) % ticker_list_column_size == 0 else len(upbit_tickers) // ticker_list_column_size + 1
    for i in range(list_size):    # ticker_list_column_size 씩 묶어서 nested list 생성
        if i * ticker_list_column_size + ticker_list_column_size > len(upbit_tickers):
            ll = upbit_tickers[i * ticker_list_column_size:len(upbit_tickers)]
        else:
            ll = upbit_tickers[i * ticker_list_column_size: i * ticker_list_column_size + ticker_list_column_size]
        l.append(ll)
    for tickers in l:
        row = ticker_list.columns(ticker_list_column_size)
        for i, ticker in enumerate(tickers):
            with row[i]:
                st.checkbox(ticker, value=True, key=f"{ticker}_ticker_checkbox")
    query_target_tickers = []
    for ticker in upbit_tickers:
        if st.session_state[f"{ticker}_ticker_checkbox"]:
            query_target_tickers.append(ticker)

    total_ticker_checkbox_count = len(upbit_tickers)
    print(f"checked: {len(query_target_tickers)} / unchecked: {total_ticker_checkbox_count - len(query_target_tickers)}")


##############################
# 조회 Unit 선택 영역
##############################
unit_list_column_size = 6

with st.expander("업데이트할 Candle 단위 선택"):
    unit_list = st.container(height=200)

    units = ["months", "weeks", "days", "240분", "60분", "30분", "15분", "10분", "5분", "3분", "1분"]
    l = []
    list_size = len(units) // unit_list_column_size if len(units) % unit_list_column_size == 0 else len(units) // unit_list_column_size + 1
    for i in range(list_size):
        if i * unit_list_column_size + unit_list_column_size > len(units):
            ll = units[i * unit_list_column_size:len(units)]
        else:
            ll = units[i * unit_list_column_size: i * unit_list_column_size + unit_list_column_size]
        l.append(ll)
    for us in l:
        row = unit_list.columns(unit_list_column_size)
        for i, unit in enumerate(us):
            with row[i]:
                if unit in ["240분", "60분"]:
                    st.checkbox(unit, value=True, key=f"{unit}_unit_checkbox")
                else:
                    st.checkbox(unit, value=False, key=f"{unit}_unit_checkbox")
    query_target_units = []
    for unit in units:
        if st.session_state[f"{unit}_unit_checkbox"]:
            query_target_units.append(unit)

    total_unit_checkbox_count = len(units)
    print(f"checked units: {len(query_target_units)} / unchecked units: {total_unit_checkbox_count - len(query_target_units)}")


##############################
# 조회 시작 / 중지 버튼
##############################

if "is_updating" not in st.session_state: st.session_state["is_updating"] = False  # 업데이트 상태 추가
update_start_stop_button_container = st.container()
ussbc_cols = update_start_stop_button_container.columns(6)
with ussbc_cols[0]:
    if st.button("업데이트 시작", key="update_start_button", disabled=st.session_state["is_updating"]):
        st.session_state["is_updating"] = True
        st.rerun()
with ussbc_cols[1]:
    if st.button("업데이트 중지", key="update_stop_button", disabled=not st.session_state["is_updating"]):
        st.session_state["is_updating"] = False
        st.rerun()

##############################
# 메세지 출력 공간
##############################
        
# streamlit page 에 진행상황 표시할 위치 생성
if "ohlcpv_update_message" not in st.session_state: 
    st.session_state["ohlcpv_update_message"] = "Request OHLCPV from Upbit -\tWaiting for update to start."
ohlcpv_message_area = st.empty()
ohlcpv_message_area.text(st.session_state["ohlcpv_update_message"])

if "indicators_update_message" not in st.session_state:
    st.session_state["indicators_update_message"] = "Calculate Indicators \t  -\tWaiting for update to start."
indicators_message_area = st.empty()
indicators_message_area.text(st.session_state["indicators_update_message"])

if "evaluations_update_message" not in st.session_state:
    st.session_state["evaluations_update_message"] = "Evaluate status \t  -\tWaiting for update to start."
evaluations_message_area = st.empty()
evaluations_message_area.text(st.session_state["evaluations_update_message"])

if "volume_powers_update_message" not in st.session_state:
    st.session_state["volume_powers_update_message"] = "Volume Power Query status -\tWaiting for update to start."
volume_powers_message_area = st.empty()
volume_powers_message_area.text(st.session_state["volume_powers_update_message"])

##############################
# 작업 수행 호출
##############################
if "update_ever_happened" not in st.session_state:
    st.session_state["update_ever_happened"] = False

if st.session_state["is_updating"]:
    update_ohlcpvs(query_target_tickers, query_target_units)
    update_indicators(query_target_tickers, query_target_units)
    update_evaluations(query_target_tickers, query_target_units)
    update_volume_powers(query_target_tickers, query_target_units)

    # update 발생 기록
    st.session_state["update_ever_happened"] = True

    # 업데이트 시작/중지 버튼 새로고침
    st.session_state["is_updating"] = False
    st.rerun()

##############################
# 작업 수행 후 출력 공간
##############################

def show_BOOK_dataframe(tickers, units):

    global BOOK

    # BOOK 내용 불러오기
    load_BOOK_data()

    # 보여줄 마켓 목록 생성
    targets = [f"{ticker},{unit}" for ticker in tickers for unit in units]

    # dataframe 설정
    columns = ["RSI", "MACD", "Williams %R", "Volume Power"]
    index   = targets

    df = pd.DataFrame(columns=columns, index=index)

    for target in targets:
        ticker, unit = target.split(",")

        series_d = {}

        # RSI
        series_d["RSI"] = BOOK[target]["eval"]["RSI"]

        # MACD
        series_d["MACD"] = BOOK[target]["eval"]["MACD"]

        # Williams %R
        series_d["Williams %R"] = BOOK[target]["eval"]["Williams%R"]

        # volume power
        series_d["Volume Power"] = BOOK[target]["volume_power"]

        df.loc[target] = pd.Series(series_d)

    # highlight 
    # df = df.style.applymap(df_color_indicator_text, subset=["RSI", "MACD", "Williams %R"])
    df = df.style.map(df_color_indicator_text, subset=["RSI", "MACD", "Williams %R"])

    # show dataframe
    st.session_state["dataframe_area"].dataframe(df)

    return

# def create_dataframe():

#     d = {}
    
#     index = []
#     rsi = []
#     rsi_line = []
#     macd = []
#     macd_oscillator_line = []
#     williamsr = []
#     williamsr_line = []
#     volumepower = []

#     columns = ["RSI", "RSI_line", "MACD","MACD_osc_line", "Williams %R","Williams %R_line", "Volume Power"]

#     global BOOK

#     for key in BOOK:

#         ticker, unit = key.split(",")
        
#         index.append(key)

#         # RSI
#         rsi.append(BOOK[key]["eval"]["RSI"])
#         rsi_line_data = [v if v is not None else 0 for v in BOOK[key]["RSI"]][:50][::-1]
#         rsi_line.append(rsi_line_data)

#         # MACD
#         macd.append(BOOK[key]["eval"]["MACD"])
#         macd_line_data = [v if v is not None else 0 for v in BOOK[key]["MACD"]]
#         macd_signal_line_data = [v if v is not None else 0 for v in BOOK[key]["MACD_signal"]]
#         macd_oscillator_line_data = list(map(lambda x: x[0] - x[1], zip(macd_line_data, macd_signal_line_data)))[:50][::-1]
#         macd_oscillator_line.append(macd_oscillator_line_data)

#         # Williams %R
#         williamsr.append(BOOK[key]["eval"]["Williams%R"])
#         williamsr_line_data = [v if v is not None else 0 for v in BOOK[key]["Williams%R"]][:50][::-1]
#         williamsr_line.append(williamsr_line_data)

#         # Volume Power
#         volumepower.append(BOOK[key]["VolumePower"])

#     df = pd.DataFrame(list(zip(rsi, rsi_line, macd,macd_oscillator_line, williamsr,williamsr_line, volumepower)), index=index, columns=columns)
#     df = df.style.applymap(df_color_indicator_text, subset=["RSI", "MACD", "Williams %R"])
#     # st.dataframe(df.style.applymap(df_color_text, subset=["RSI", "MACD", "Williams %R"]), width=800, height=900)
#     # st.data_editor(df, column_config={
#     #     "RSI_line": st.column_config.LineChartColumn(
#     #         "RSI line chart (200)"
#     #     )
#     # })
#     st.dataframe(
#         df, 
#         column_config={
#             "RSI_line": st.column_config.LineChartColumn(
#                 label = "RSI line chart (50)",
#                 width = "small",
#                 y_min = 0,
#                 y_max = 100
#             ),
#             "MACD_osc_line": st.column_config.LineChartColumn(
#                 label = "MACD osc line chart (50)",
#                 width = "small",
#             ),
#             "Williams %R_line": st.column_config.LineChartColumn(
#                 label = "Williams %R line chart (50)",
#                 width = "small",
#                 y_min = -100,
#                 y_max = 0
#             )
#         }, 
#         width=1600, 
#         height=1000
#     )

#     return

def df_color_indicator_text(value):

    value = str(value)
    match_red1 = True if "과매도" in value else False
    match_red2 = True if "골든크로스" in value else False
    match_blue1 = True if "과매수" in value else False
    match_blue2 = True if "데드크로스" in value else False

    if match_red1 or match_red2:
        style = f'color: red'
    elif match_blue1 or match_blue2:
        style = f'color: blue'
    else:
        style = f""

    return style

def df_color_volume_power_text(value):

    pass

class txt_color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


if st.session_state["update_ever_happened"]:
    if "dataframe_area" not in st.session_state:
        st.session_state["dataframe_area"] = st.empty()

    show_BOOK_dataframe(query_target_tickers, query_target_units)

# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================



