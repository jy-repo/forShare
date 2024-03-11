import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd
import numpy as np
import requests
import time
import datetime
import re
import threading
import asyncio

# from upbit_logics import get_all_tickers_candles

###############################################################################
# Page Layout
###############################################################################
def refresh_progress_bar(value, text):
    st.session_state["bar_progress"].progress(value, text=text)
# 제목
st.title('sasdf')

# Create a sidebar
st.sidebar.title('Sidebar Title')
st.sidebar.write('This is a Streamlit sidebar example.')

#######################################
# 업데이트
#######################################

# # 업데이트 시작/중지 버튼
# update_button_001 = "update_button_001"     # 업데이트 시작/중단 버튼
# if update_button_001 not in st.session_state:       # 업데이트 버튼 추가
#     st.session_state[update_button_001] = False     # 초기 세팅 버튼 값 : False - 업데이트 불가능 (초기값 또는 동작중)

# if not st.session_state[update_button_001]:         # 업데이트 대기
#     def start_logic():
#         loop = asyncio.get_event_loop()
#         loop.run_until_complete(get_all_tickers_candles())
#         loop.close()
#     st.button("업데이트 시작", on_click=start_logic)
#     st.session_state[update_button_001] = True      # 업데이트 가능 상태로 변경
# else:                                               # 업데이트 중
#     st.button("업데이트 중지", on_click=None)
#     st.session_state[update_button_001] = False

# # 업데이트 상태 출력
# update_status_001 = "update_status_001"     # 동작 상태
# UPDATE_STATUS_001_MESSAGE_WAITING = "STATUS: 대기중"
# UPDATE_STATUS_001_MESSAGE_WORKING = "STATUS: 업데이트중"
# if update_status_001 not in st.session_state: st.session_state[update_status_001] = ""
# if st.session_state[update_button_001]:             # 업데이트 대기
#     st.session_state[update_status_001] = UPDATE_STATUS_001_MESSAGE_WAITING
# else:                                               # 업데이트 중
#     st.session_state[update_status_001] = UPDATE_STATUS_001_MESSAGE_WORKING
# st.write(st.session_state[update_status_001])


# # 업데이트 상세 출력 1
# update_detail_001 = "update_detail_001"
# if update_detail_001 not in st.session_state: st.session_state[update_detail_001] = "OHLCV 조회 (초당 최대 9회 제한 by 업비트) : 상세설명 1"
# st.text(st.session_state[update_detail_001])

# # 업데이트 상세 출력 2
# update_detail_002 = "update_detail_002"
# if update_detail_002 not in st.session_state:
#     st.session_state[update_detail_002] = "OHLCV 조회 (초당 최대 9회 제한 by 업비트) : 상세설명 1"
# st.write(st.session_state[update_detail_002])

# # 업데이트 상세 출력 3
# update_detail_003 = "update_detail_003"
# if update_detail_003 not in st.session_state:
#     st.session_state[update_detail_003] = "OHLCV 조회 (초당 최대 9회 제한 by 업비트) : 상세설명 1"
# st.write(st.session_state[update_detail_003])


# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================
# ==================================================================================================================================

import requests
import json
import time

BOOK = {}
BOOK_PATH = "book.json"

###############################################################################
# Upbit Query
###############################################################################

def get_all_tickers_candles():

    global BOOK

    # JSON 기록 불러오기
    load_BOOK_data()

    # 조회할 티커 + unit 조합 만들기
    targets = set_targets()

    # query 요청 수행 설정
    time_mark = time.time()
    query_count_in_1s = 0

    # streamlit text status
    t = st.empty()

    # query 요청 수행
    temp_cnt = 0
    for i, (ticker, unit) in enumerate(targets):

        time.sleep(0.01)
        
        temp_cnt += 1
        if temp_cnt > 999: break    # 디버그용

        # key (for BOOK)
        key = f"{ticker},{unit}"

        # ohlcpv 업데이트 해야하는지 확인
        update_needed = need_to_update_ohlcpv(key)
        tu = f"[ {ticker}, {unit} ]"
        message = f"Request OHLCPV from Upbit -\t{i+1: 3d} / {len(targets)} working on : {tu:23s}" + ('' if update_needed else '\tcached')
        print(message)
        t.text(message)
        if not update_needed: continue

        # query 요청 제어 (1초당 10개 이하로 유지)
        query_count_in_1s += 1
        if query_count_in_1s >= 9 and time.time() - time_mark < 1:  # 1초 안됨. 1초 기다리기. 이후 조회수 초기화
            time.sleep(1); query_count_in_1s = 0; time_mark = time.time()

        # query 요청 후 ohlcpv 추출
        query_unit = f"{unit}" if unit in ["months", "weeks", "days"] else f"minutes/{unit}"
        url = f"https://api.upbit.com/v1/candles/{query_unit}?market={ticker}&count=200"
        response = requests.get(url)
        candles = response.json()
        ohlcpv = candles_to_ohlcpv(candles)

        # 저장
        if key not in BOOK: BOOK[key] = {}
        for key2 in ohlcpv:
            BOOK[key][key2] = ohlcpv[key2]
            BOOK[key]["last_ohlcpv_update_time"] = time.time()

    # stream text status
    now = datetime.datetime.now()
    t.text(f"Request OHLCPV from Upbit -\t업데이트 완료 ( {now} )")

    # book to json file
    with open(BOOK_PATH, 'w', encoding="utf8") as f:
        json.dump(BOOK, f)
    
    return

def load_BOOK_data():

    global BOOK

     # load JSON data if it exist
    try:
        with open(BOOK_PATH, 'r', encoding="utf8") as f:
            BOOK = json.load(f)
            print("past ohlcpv log loaded")
    except:
        print("No past ohlcpv log file. pass")
        pass

    return

def set_targets():

    # ohlcpv 업데이트할 query targets 범위 설정
    units = ["days", "240", "60", "15"]

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

def calc_all_tickers_indicators():

    global BOOK

    # streamlit text status
    t = st.empty()

    for i, key in enumerate(BOOK):

        ticker, unit = key.split(',')
        tu = f"[ {ticker}, {unit} ]"
        message = f"Calculate Indicators \t  -\t{i+1: 3d} / {len(BOOK)} working on : {tu:23s}"
        print(message)
        t.text(message)

        dt_ksts = BOOK[key]["date_time_ksts"]
        opens = BOOK[key]["opens"]
        highs = BOOK[key]["highs"]
        lows = BOOK[key]["lows"]
        trades = BOOK[key]["trades"]
        tot_prices = BOOK[key]["tot_prices"]
        tot_volumes = BOOK[key]["tot_volumes"]

        # RSI
        RSIs = get_RSIs(trades)
        BOOK[key]["RSI"] = RSIs

        # MACD
        MACDs, MACD_signals = get_MACDs(trades)
        BOOK[key]["MACD"] = MACDs
        BOOK[key]["MACD_signal"] = MACD_signals

        # Williams %R
        WilliamsRs = get_WilliamsR(highs, lows, trades)
        BOOK[key]["Williams%R"] = WilliamsRs


        # 보조지표 계산 맞는지 체크용 3개씩 출력
        # print(key)
        # for i in range(3):
        #     print(dt_ksts[i], end=" ")
        #     print(trades[i], end=" ")
        #     print("RSI", round(RSIs[i], 2), end=" ")
        #     print("MACD", round(MACDs[i], 2), end=" ")
        #     print("MACD signal", round(MACD_signals[i], 2))
        #     print("Williams%R", round(WilliamsRs[i], 2))

    # stream text status
    now = datetime.datetime.now()
    t.text(f"Calculate Indicators \t  -\t업데이트 완료 ( {now} )")

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

def evaluate_all_tickers():

    global BOOK

    # streamlit text status
    t = st.empty()

    for i, key in enumerate(BOOK.keys()):

        if "eval" not in BOOK[key]: BOOK[key]["eval"] = {}

        ticker, unit = key.split(',')
        tu = f"[ {ticker}, {unit} ]"
        message = f"Evaluate status \t  -\t{i+1: 3d} / {len(BOOK)} working on : {tu:23s}"
        print(message)
        t.text(message)

        RSIs = BOOK[key]["RSI"]
        RSI_status = get_RSI_status(RSIs)
        BOOK[key]["eval"]["RSI"] = RSI_status

        MACDs = BOOK[key]["MACD"]
        MACD_signals = BOOK[key]["MACD_signal"]
        MACD_status = get_MACD_status(MACDs, MACD_signals)
        BOOK[key]["eval"]["MACD"] = MACD_status

        WilliamsRs = BOOK[key]["Williams%R"]
        WilliamsR_status = get_WilliamsR_status(WilliamsRs)
        BOOK[key]["eval"]["Williams%R"] = WilliamsR_status

    # stream text status
    now = datetime.datetime.now()
    t.text(f"Evaluate status \t  -\t업데이트 완료 ( {now} )")

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
# Driver
###############################################################################

def driver():

    # OHLCPV
    get_all_tickers_candles()

    # Volume Power (거래강도)
    # tickers_VPs_d = get_all_tickers_VPs()
        
    # 보조지표 
    calc_all_tickers_indicators()

    # 평가 (필터링)
    evaluate_all_tickers()

    #### 확인용 ####
    # for key in BOOK:
    #     print("logbook key:", key)

    #     print("\t", BOOK[key]["RSI"][0:3])
    #     print("\t", BOOK[key]["eval"]["RSI"])
    #     print("\t", BOOK[key]["MACD"][0:3])
    #     print("\t", BOOK[key]["MACD_signal"][0:3])
    #     print("\t", BOOK[key]["eval"]["MACD"])
    #     print("\t", BOOK[key]["Williams%R"][0:3])
    #     print("\t", BOOK[key]["eval"]["Williams%R"])

    # book to json file
    with open(BOOK_PATH, 'w', encoding="utf8") as f:
        json.dump(BOOK, f)

    return

def print_evals():

    
    global BOOK

    # JSON 기록 불러오기
    load_BOOK_data()

    for key in BOOK:
        time.sleep(0.01)
        ticker, unit = key.split(",")

        # 키별 판단값 출력
        
        # streamlit
        t = st.empty()

        # 출력문 생성
        streamlit_strs = []
        line_strs = []

        streamlit_strs.append(f"> {key:20s}")
        line_strs.append(f"> {key:20s}")

        # RSI
        RSI_status = BOOK[key]["eval"]["RSI"]
        
        if RSI_status.startswith("과매도"):
            streamlit_strs.append(f"RSI: :red[{RSI_status}]")
            line_strs.append(txt_color.RED + RSI_status + txt_color.ENDC)
        elif RSI_status.startswith("과매수"):
            streamlit_strs.append(f"RSI: :blue[{RSI_status}]\t")
            line_strs.append(txt_color.BLUE + RSI_status + txt_color.ENDC)
        else:
            streamlit_strs.append(f"RSI: {RSI_status}")
            line_strs.append(f"RSI: {RSI_status:15s}")

        # MACD
        MACD_status = BOOK[key]["eval"]["MACD"]
        if MACD_status.startswith("골든크로스"):
            streamlit_strs.append(f"MACD: :red[{MACD_status}]")
            line_strs.append(txt_color.RED + MACD_status + txt_color.ENDC)
        elif MACD_status.startswith("데드크로스"):
            streamlit_strs.append(f"MACD: :blue[{MACD_status}]")
            line_strs.append(txt_color.BLUE + MACD_status + txt_color.ENDC)
        else:
            streamlit_strs.append(f"MACD: {MACD_status}")
            line_strs.append(f"MACD: {MACD_status:15s}")

        # Williams %R
        WilliamsR_status = BOOK[key]["eval"]["Williams%R"]
        if WilliamsR_status.startswith("과매도"):
            streamlit_strs.append(f"Williams %R: :red[{WilliamsR_status}]")
            line_strs.append(txt_color.RED + WilliamsR_status + txt_color.ENDC)
        elif WilliamsR_status.startswith("과매수"):
            streamlit_strs.append(f"Williams %R: :blue[{WilliamsR_status}]")
            line_strs.append(txt_color.BLUE + WilliamsR_status + txt_color.ENDC)
        else:
            streamlit_strs.append(f"Williams %R: {WilliamsR_status}")
            line_strs.append(f"Williams %R: {WilliamsR_status:15s}")

        streamlit_str = "\t".join(streamlit_strs)
        line = "\t".join(line_strs)

        st.write(streamlit_str)        
        print(line)

    return

def create_dataframe():

    d = {}
    
    index = []
    rsi = []
    macd = []
    williamsr = []

    global BOOK

    for key in BOOK:

        ticker, unit = key.split(",")
        
        index.append(key)
        rsi.append(BOOK[key]["eval"]["RSI"])
        macd.append(BOOK[key]["eval"]["MACD"])
        williamsr.append(BOOK[key]["eval"]["Williams%R"])

    df = pd.DataFrame(list(zip(rsi, macd, williamsr)), index=index, columns=["RSI", "MACD", "William %R"])
    df.style.applymap(df_color_text,subset=["RSI", "MACD", "William %R"])

    st.dataframe(df, width=800, height=900)

    return

def df_color_text(value):

    match_red1 = re.search(r"과매수", value)
    match_red2 = re.search(r"골든크로스", value)
    match_blue1 = re.search(r"과매도", value)
    match_blue2 = re.search(r"데드크로스", value)

    if match_red1 or match_red2:
        f'color: red'
    else:
        f'color: blue'

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


driver()

create_dataframe()