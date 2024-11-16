import streamlit as st
import stock_analysis_lib as glib
import stock_analysis_database_lib as databaselib
from langchain.callbacks import StreamlitCallbackHandler
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Enter 키 처리를 위한 함수
def handle_input():
    if not st.session_state.get('enter_pressed', False):
        st.session_state.enter_pressed = True
        st.rerun()

def print_result(st, response):
    try:
        st.subheader("일별 주가:")
        st.dataframe(response['intermediate_steps'][1][1], use_container_width=True)
    except Exception as e:
        print(f"Fail to draw price data table: {str(e)}")

    try:
        st.subheader("주가 차트:")
        df = pd.DataFrame(response['intermediate_steps'][1][1], columns=['Close', 'Open', 'High', 'Low', 'Volume'])
        df['Volume'] = df['Volume']/5000000
        df.rename(columns={
            'Close': 'Close', 
            'Open': 'Open', 
            'High': 'High', 
            'Low': 'Low', 
            'Volume': 'Volume(10 millions)'
        }, inplace=True)

        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Candlestick'
        ))
        
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], mode='lines', name='MA5'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='MA20'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='MA60'))
        fig.add_trace(go.Bar(x=df.index, y=df['Volume(10 millions)'], name='Volume'))

        fig.update_layout(
            title=' ',
            xaxis_title='Date',
            yaxis_title='Price(USD)',
            yaxis2=dict(
                title='Volume(10 millions)', 
                tickvals=df['Volume(10 millions)'], 
                overlaying='y', 
                side='right'
            ),
            xaxis_rangeslider_visible=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig)
    except Exception as e:
        print(f"Fail to draw price chart: {str(e)}")
        
    try:
        st.subheader("재무 제표:")
        fs_df = pd.DataFrame(response['intermediate_steps'][3][1])
        fs_df.columns = pd.to_datetime(fs_df.columns, format='%Y-%m-%d').year
        st.dataframe(fs_df, use_container_width=True)
    except Exception as e:
        print(f"Fail to draw financial statement: {str(e)}")

    try:
        st.subheader("분석 결과:")
        st.write(response['output'])
    except Exception as e:
        st.write(response['output'])

def add_stt_component():
    components.html(
        """
        <div id="speech-container">
            <style>
                .mic-button {
                    background-color: transparent;
                    border: 2px solid #4B9CD3;
                    border-radius: 50%;
                    width: 50px;
                    height: 50px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 10px auto;
                    transition: all 0.3s ease;
                    padding: 0;
                }
                .mic-button:hover {
                    background-color: rgba(75,156,211,0.1);
                }
                .mic-button.recording {
                    background-color: #4B9CD3;
                }
                .mic-button svg {
                    width: 24px;
                    height: 24px;
                    fill: none;
                    stroke: #4B9CD3;
                    stroke-width: 2;
                    stroke-linecap: round;
                    stroke-linejoin: round;
                }
                .mic-button.recording svg {
                    stroke: white;
                }
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(75,156,211,0.4); }
                    70% { box-shadow: 0 0 0 15px rgba(75,156,211,0); }
                    100% { box-shadow: 0 0 0 0 rgba(75,156,211,0); }
                }
                .mic-button.recording {
                    animation: pulse 1.5s infinite;
                }
                #sttStatus {
                    text-align: center;
                    margin-top: 10px;
                    font-size: 14px;
                    min-height: 20px;
                    color: #4B9CD3;
                }
            </style>

            <button id="micButton" class="mic-button" onclick="toggleRecording()">
                <svg viewBox="0 0 24 24">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
            </button>
            <div id="sttStatus"></div>

            <script>
                var recognition = null;
                var isRecording = false;
                var lastTranscript = '';
                var isProcessing = false;

                function findSearchButton() {
                    const buttons = window.parent.document.getElementsByTagName('button');
                    for (let button of buttons) {
                        if (button.textContent && button.textContent.includes('검색')) {
                            return button;
                        }
                    }
                    return null;
                }

                function setInputValue(input, value) {
                    const prototype = Object.getPrototypeOf(input);
                    const setter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    setter.call(input, value);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }

                function updateInputAndTriggerSearch(text) {
                    if (isProcessing) return;
                    isProcessing = true;

                    const targetInput = window.parent.document.querySelector('input[aria-label="여기에 회사 이름 입력하세요!"]');
                    const baseInputDiv = window.parent.document.querySelector('div[data-baseweb="input"]');
                    const searchButton = findSearchButton();
                    
                    if (targetInput && searchButton) {
                        // value 설정
                        setInputValue(targetInput, text);
                        lastTranscript = text;

                        // React state 업데이트를 위한 이벤트 발생
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(targetInput, text);

                        // 입력 값 유지를 위한 MutationObserver
                        const observer = new MutationObserver((mutations) => {
                            mutations.forEach((mutation) => {
                                if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                                    const currentValue = targetInput.value;
                                    if (currentValue !== text) {
                                        setInputValue(targetInput, text);
                                    }
                                }
                            });
                        });

                        observer.observe(targetInput, {
                            attributes: true,
                            attributeFilter: ['value']
                        });

                        // 이벤트 리스너 추가
                        function maintainValue(e) {
                            if (e.target.value !== text) {
                                e.preventDefault();
                                setInputValue(targetInput, text);
                            }
                        }

                        ['input', 'change', 'focus', 'blur', 'click'].forEach(eventType => {
                            targetInput.addEventListener(eventType, maintainValue, true);
                        });

                        // 검색 버튼 클릭
                        setTimeout(() => {
                            searchButton.click();
                            isProcessing = false;
                        }, 100);
                    }
                }

                function initializeSpeechRecognition() {
                    if (!('webkitSpeechRecognition' in window)) {
                        alert('이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 브라우저를 사용해주세요.');
                        return null;
                    }

                    const recognition = new webkitSpeechRecognition();
                    recognition.lang = 'ko-KR';
                    recognition.continuous = false;
                    recognition.interimResults = true;

                    recognition.onstart = () => {
                        isRecording = true;
                        document.getElementById('micButton').classList.add('recording');
                        document.getElementById('sttStatus').textContent = '말씀해주세요...';
                    };

                    recognition.onend = () => {
                        isRecording = false;
                        document.getElementById('micButton').classList.remove('recording');
                        document.getElementById('sttStatus').textContent = '';
                    };

                    recognition.onresult = (event) => {
                        const results = event.results;
                        const transcript = results[results.length - 1][0].transcript;
                        document.getElementById('sttStatus').textContent = transcript;

                        if (results[results.length - 1].isFinal) {
                            updateInputAndTriggerSearch(transcript.trim());
                            recognition.stop();
                        }
                    };

                    recognition.onerror = (event) => {
                        console.error('Speech recognition error:', event.error);
                        document.getElementById('sttStatus').textContent = 
                            '음성 인식 오류가 발생했습니다. 다시 시도해주세요.';
                        isRecording = false;
                        document.getElementById('micButton').classList.remove('recording');
                    };

                    return recognition;
                }

                function toggleRecording() {
                    if (!recognition) {
                        recognition = initializeSpeechRecognition();
                    }

                    if (!isRecording && recognition) {
                        recognition.start();
                    } else if (recognition) {
                        recognition.stop();
                    }
                }

                // DOM 로드 완료 후 초기화
                window.addEventListener('load', () => {
                    const targetInput = window.parent.document.querySelector('input[aria-label="여기에 회사 이름 입력하세요!"]');
                    if (targetInput) {
                        const config = { attributes: true, characterData: true, childList: true };
                        const observer = new MutationObserver((mutations) => {
                            mutations.forEach((mutation) => {
                                if (lastTranscript && targetInput.value !== lastTranscript) {
                                    setInputValue(targetInput, lastTranscript);
                                }
                            });
                        });
                        observer.observe(targetInput, config);
                    }
                });

                // Enter 키 이벤트 처리
                window.parent.document.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        const searchButton = findSearchButton();
                        if (searchButton) {
                            searchButton.click();
                        }
                    }
                });
            </script>
        </div>
        """,
        height=100
    )

def stock_analysis():
    st.title("KB증권 GenAI Stock Agent")
    st.subheader("주식 분석을 위한 AI 투자 자문")
    st.write("Amazon, Tesla, Apple 등과 같은 회사명으로 입력해보세요 :)")

    # 데이터베이스 초기화
    try:
        if 'database' not in st.session_state:
            with st.spinner("Initializing Database..."):
                if hasattr(databaselib, 'initial_database'):
                    databaselib.initial_database()
                else:
                    st.error("Database initialization function not found!")
                    return
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")
        return

    # 채팅 기록 초기화
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # 에이전트 초기화
    try:
        agent = glib.initializeAgent()
    except Exception as e:
        st.error(f"Error initializing agent: {str(e)}")
        return

    # STT 컴포넌트 추가
    st.write("음성으로 검색하시려면 마이크 버튼을 눌러주세요")
    add_stt_component()
    
    # 입력 필드와 검색 결과 영역
    col1, col2 = st.columns([5, 1])
    
    # 검색어 입력 필드
    with col1:
        input_text = st.text_input(
            "여기에 회사 이름 입력하세요!", 
            key="text_input",
            on_change=handle_input
        )
    
    # 검색 버튼
    with col2:
        search_button = st.button("검색", type="primary")

    # 검색 실행 (Enter 키나 검색 버튼 클릭 시)
    should_search = search_button or st.session_state.get('enter_pressed', False)
    
    if should_search and input_text:
        # Enter 키 상태 초기화
        if 'enter_pressed' in st.session_state:
            st.session_state.enter_pressed = False
            
        with st.spinner("분석 중..."):
            try:
                st_callback = StreamlitCallbackHandler(st.container())
                response = agent({
                    "input": input_text,
                    "today": date.today(),
                    "chat_history": st.session_state.chat_history,
                }, callbacks=[st_callback])
                
                print_result(st, response)
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    stock_analysis()
