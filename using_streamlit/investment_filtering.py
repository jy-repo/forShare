import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# widgets keys
update_button_001 = "update_button_001"     # 업데이트 시작/중단 버튼
update_status_001 = "update_status_001"     # 현상태
update_status_002 = "update_status_002"     # 상세 진행 상태



def update_all():

    # get all tickers
    query_market_tickers_url = "https://api.upbit.com/v1/market/all"
    response = requests.get(query_market_tickers_url)

    # ohlcv update
    targets = [target for target in response.json() if target["market"].startswith("KRW-")]
    units = ["days", "240", "60", "15"]

    ohlcavs_per_tu = {}
    for target in targets:
        for unit in units:
            print(target, unit)
            category = f"minutes/{unit}" if unit.isnumeric() else unit
            query_url = f"https://api.upbit.com/v1/candles/{category}?market={target['market']}&count=200"
            headers = {"accept": "application/json"}
            response = requests.get(query_url, headers=headers)
            
            ohlcavs_per_tu[(target["market"], unit)] = response.json()

            # for candle in response.json():
            #     market = candle["market"]
            #     datetime_utc = candle["candle_date_time_utc"]
            #     datetime_kst = candle["candle_date_time_kst"]
            #     open = candle["opening_price"]
            #     high = candle["high_price"]
            #     low = candle["low_price"]
            #     trade = candle["trade_price"]
            #     amount = candle["candle_acc_trade_price"]
            #     volume = candle["candle_acc_trade_volume"]

            time.sleep(0.2)
            break
        break

    # calculate indicators
    def RSI(closes, period=14):
        '''
            closes : [현재 -> 과거] 순 종가 목록
        '''
        closes = closes[::-1]
        differences = [0] + [closes[i+1] - closes[i] for i in range(len(closes) - 1)]
        diff_U = [d if d > 0 else 0 for d in differences]
        diff_D = [-d if d < 0 else 0 for d in differences]
        ewm_a = 1 / (1 + (period - 1))
        ewm_U = [0]
        ewm_D = [0]
        for U in diff_U: ewm_U.append(U * ewm_a + ewm_U[-1] * ewm_a)
        for D in diff_D: ewm_D.append(D * ewm_a + ewm_D[-1] * ewm_a)
        ewm_U = ewm_U[1:]
        ewm_D = ewm_D[1:]
        RSs = [ewm_U[i] / ewm_D[i] if ewm_D[i] != 0 else None for i in range(len(ewm_U))]
        RSIs = [100 - (100 / (1 + RS)) if RS is not None else None for RS in RSs][::-1]
        return RSIs

    for market, unit in ohlcavs_per_tu.keys():

        ohlcavs = ohlcavs_per_tu[(market, unit)]

        closes = [ohlcav["trade_price"] for ohlcav in ohlcavs]
        RSIs = RSI(closes)
        print(ohlcavs[0]["market"])
        print(RSIs)


# 제목
st.title('CCCCCCCCCC')

# 업데이트 버튼
is_updating = "is_updating"
if is_updating not in st.session_state:
    st.session_state[is_updating] = False

if not st.session_state[is_updating]:               # 업데이트 중
    def start_update():
        st.session_state[update_status] = "working"
        update_all()
    btn = st.button("업데이트", on_click=start_update)
    st.session_state[is_updating] = False
else:                                               # 업데이트 대기 중
    def stop_update():
        st.session_state[update_status] = "stopped"
    btn = st.button("업데이트 중", on_click=stop_update)
    st.session_state[is_updating] = True

# 업데이트 상태 출력
update_status = "update_status"
if update_status not in st.session_state:
    st.session_state[update_status] = "Idle"

st.write(st.session_state[update_status])

