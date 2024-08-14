import streamlit as st 
import stock_analysis_lib as glib 
import stock_analysis_database_lib as databaselib 
from langchain.callbacks import StreamlitCallbackHandler
import time
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
'''
def print_result(st, response):
    try:
        st.subheader("Daily sticker:")
        st.dataframe(response['intermediate_steps'][1][1])
        st.subheader("Stock Chart:")
        df = pd.DataFrame(response['intermediate_steps'][1][1],columns=['Close','Volume'])
        df['Volume'] = df['Volume']/10000000
        df.rename(columns={'Close':'Price(USD)','Volume':'Volume(10 millions)'},inplace=True)
        st.line_chart(df)
        st.subheader("Conclusion:")
        st.write(response['output'])
    except:
        st.write(response['output'])
'''
def print_result(st, response):
    try:
        st.subheader("일별 주가:")
        st.dataframe(response['intermediate_steps'][1][1], use_container_width=True)

        # 1. 주가 데이터 표로 출력
        # 1.1 데이터프레임 준비
        '''
        df = pd.DataFrame(response['intermediate_steps'][1][1], columns=['Close', 'Open', 'High', 'Low', 'Volume'])

        # 1.2 인덱스를 datetime 형식으로 변환
        df.index = pd.to_datetime(df.index)

        # 1.3 날짜만 추출하여 새로운 열 생성
        df['Date'] = df.index.date

        # 1.4 'Date' 열을 인덱스로 설정
        df = df.set_index('Date')

        # 1.5 데이터프레임 출력
        st.dataframe(df.style.format({
            'Close': '{:.2f}',
            'Open': '{:.2f}',
            'High': '{:.2f}',
            'Low': '{:.2f}',
            'Volume': '{:,.0f}'
        }), use_container_width=True)
        '''
    except:
        print("Fail to draw price data table")

    try:
        # 2. 주가 데이터 차트로 출력
        st.subheader("주가 차트:")

        # 2.1 데이터 준비
        #df = pd.DataFrame(response['intermediate_steps'][1][1], columns=['Close', 'Volume'])
        df = pd.DataFrame(response['intermediate_steps'][1][1], columns=['Close', 'Open', 'High', 'Low', 'Volume'])
        df['Volume'] = df['Volume']/5000000
        #df.rename(columns={'Close': 'Price(USD)', 'Volume': 'Volume(10 millions)'}, inplace=True)
        df.rename(columns={'Close': 'Close', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Volume': 'Volume(10 millions)'}, inplace=True)

        # 이동평균선 계산
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 2.2 그래프 생성
        fig = go.Figure()

        # 2.3 가격 차트 추가
        #fig.add_trace(go.Scatter(x=df.index, y=df['Price(USD)'], mode='lines', name='Price(USD)'))
        # Candlestick 차트 추가
        fig.add_trace(go.Candlestick(x=df.index,
                                    open=df['Open'],
                                    high=df['High'],
                                    low=df['Low'],
                                    close=df['Close'],
                                    name='Candlestick'))
        
        # 이동평균선 추가
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], mode='lines', name='MA5'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='MA20'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='MA60'))

        # 2.4 거래량 차트 추가 (막대 그래프)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume(10 millions)'], name='Volume'))

        # 2.5 레이아웃 설정
        fig.update_layout(
            title=' ',
            xaxis_title='Date',
            yaxis_title='Price(USD)',
            yaxis2=dict(title='Volume(10 millions)', tickvals=df['Volume(10 millions)'], overlaying='y', side='right'),
            xaxis_rangeslider_visible=True,  # 범위 슬라이더 추가
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)  # 레전드 위치 변경
        )
        # 대화형 그래프 출력
        st.plotly_chart(fig)
    except:
        print("Fail to draw price chart")
        
    try:
        # 3. 재무 제표 출력
        st.subheader("재무 제표:")
        print(response['intermediate_steps'][3][1])
        fs_df = pd.DataFrame(response['intermediate_steps'][3][1])
        fs_df.columns = pd.to_datetime(fs_df.columns, format='%Y-%m-%d').year
        st.dataframe(fs_df, use_container_width=True)

        #st.write(fs_df)
    except:
        print("Fail to draw financial statement")

    try:
        # 4. 결과 보고서 출력
        st.subheader("분석 결과:")
        st.write(response['output'])
    except:
        st.write(response['output'])

def stock_analysis():
    st.title("GenAI Stock Agent")
    st.subheader("주식 분석을 위한 AI 투자 자문")
    st.write("Amazon, Tesla, Apple 등과 같은 회사명으로 입력해보세요...")

    if 'database' not in st.session_state: 
        with st.spinner("Initial Database"): 
            databaselib.initial_database() 
        
    if 'chat_history' not in st.session_state: 
        st.session_state.chat_history = [] 

    agent = glib.initializeAgent()
    input_text = st.chat_input("여기에 회사 이름 입력하세요!") 
    ph = st.empty()
    if input_text:
        ph.empty()
        st_callback = StreamlitCallbackHandler(st.container())
        response = agent({
            "input": input_text,
            "today": date.today(),
            "chat_history": st.session_state.chat_history,
         },
            callbacks=[st_callback])
        print_result(st,response)

