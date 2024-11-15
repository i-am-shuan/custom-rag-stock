import os
from langchain.llms.bedrock import Bedrock
import boto3
from langchain_aws import ChatBedrock
from langchain.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.tools import DuckDuckGoSearchRun
from langchain.prompts.chat import ChatPromptTemplate
from langchain.chains import LLMChain
from datetime import timedelta
from pandas_datareader import data as pdr
from datetime import date
from langchain.prompts.prompt import PromptTemplate
import yfinance as yf

yf.pdr_override() 
def get_llm(k = 1):
    session = boto3.Session()
    bedrock_runtime = session.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )
        
    model_parameter = {
        "max_tokens": 4096,
        "temperature": 0.0,
        "top_k": k,
        "top_p": 1.0,
        "stop_sequences": ["SQLResult: "]
    }
    
    llm = Bedrock(
        client=bedrock_runtime,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs=model_parameter,
        streaming=True)

    return llm

def get_claude3(k = 1):
    try:
        session = boto3.Session()
        bedrock_runtime = session.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )
        
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        model_kwargs = {
            "max_tokens": 4096,
            "temperature": 0.0,
            "top_k": k,
            "top_p": 1.0,
            "stop_sequences": ["\n\nHuman: "],
        }
        
        model = ChatBedrock(
            client=bedrock_runtime,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )
        return model
    except boto3.exceptions.Boto3Error as e:
        if 'ExpiredTokenException' in str(e):
            print(f"Error: {e}. The security token included in the request is expired. Please renew your AWS credentials.")
        else:
            print(f"Error initializing Claude 3.5 model: {e}")
        return None
    except Exception as e:
        print(f"Error initializing Claude 3.5 model: {e}")
        return None




def get_db_chain(prompt):
    db = SQLDatabase.from_uri("sqlite:///stock_ticker_database.db")
    llm = get_claude3(k = 1)
    db_chain = SQLDatabaseChain.from_llm(
        llm, 
        db, 
        verbose=True, 
        return_intermediate_steps=False,
        return_direct=True, 
        prompt=prompt, 
        top_k=1,
    )
    return db_chain


def get_stock_code_from_api(company_name):
    url = "https://oapi.kbsec.com/v2.0/NIVS01/search-ticker"
    headers = {
        "Content-Type": "application/json",
        "apikey": "l7xxESFi1ld7pk0ZAJKZDLGNRTcBLhtfJnRh"
    }
    data = {
        "dataHeader": {
            "udId": "UDID"
        },
        "dataBody": {
            "isNm": company_name
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        response_data = response.json()
        
        print('@@@@@@@@@@@@@@response_data: ', response_data)
        if response_data["dataHeader"]["resultCode"] == "200":
            stock_info = response_data["dataBody"]["out2"][0]
            stock_code = stock_info["isCd"].strip()
            market_class = stock_info["mktClsf"].strip()
            
            if market_class == '1':
                return f"{stock_code}.KS"
            elif market_class == '2':
                return f"{stock_code}.KQ"
    return None
    
def get_stock_ticker_api(query):
    template = """You are a helpful assistant who extracts company name from the human input. Please only output the company. If the human input is written in Korean, return the human input as the company name. If you cannot find company name, just return NONE."""
    human_template = "{text}"
    llm = get_claude3(k=1)

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    llm_chain = LLMChain(
        llm=llm,
        prompt=chat_prompt
    )

    company_name = llm_chain(query.strip())['text'].strip()
    if "NONE" == company_name:
        return None

    # TODO shuan 국내, 해외 구분하는 로직 필요
    # ProServe 팀에서는 2번 태우는것을 추천
    # 오픈 API를 통해 종목코드 조회
    company_ticker = get_stock_code_from_api(company_name)

    if not company_ticker:
        return None
    return company_ticker    

    
def get_stock_ticker(query):
    template = """You are a helpful assistant who extract company name from the human input. Please only output the company. If the human input is written in Korean, return the human input as the company name. If you can not find company name, just return NONE"""
    human_template = "{text}"
    llm = get_claude3(k = 1)

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    llm_chain = LLMChain(
        llm=llm,
        prompt=chat_prompt
    )

    company_name=llm_chain(query.strip())['text'].strip()
    if "NONE" == company_name:
        return None
    
    _DEFAULT_TEMPLATE = """Human: Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the first answer. 
<format>
Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Result of SQLResult only"
</format>
Assistant: Understood, I will use the above format and only provide the answer.

Only use the following tables:
<tables>
CREATE TABLE stock_ticker (
	symbol text PRIMARY KEY,
	name text NOT NULL,
	currency text,
	stockExchange text, 
    exchangeShortName text
)
</tables>

If someone asks for the table stock ticker table, they really mean the stock_ticker table.
<examples>
Question: 
        What is the ticker symbol for Amazon in stock ticker table?
        Params: 
        Company name (name): Amazon
        
SQLQuery:SELECT symbol FROM stock_ticker WHERE name = 'Amazon' union all SELECT symbol FROM stock_ticker WHERE name like '%Amazon%' limit 1

</examples>

Question: \n\nHuman:{input} \n\nAssistant:

"""

    PROMPT = PromptTemplate(
        input_variables=["input", "dialect"], template=_DEFAULT_TEMPLATE
)
    db_chain = get_db_chain(PROMPT)

    company_ticker = db_chain("\n\nHuman: What is the ticker symbol for " + str(company_name) + " in stock tickers table? \n\nAssistant:")

    if company_ticker['result'] == '':
        return None
    return company_ticker['result']
    
    
def get_stock_price(ticker):
    today = date.today()
    start_date = today - timedelta(days=500)
    data = pdr.get_data_yahoo(ticker, start=start_date, end=today)
    return data


# Fetch top 5 google news for given company name
import re
import requests
def google_query(search_term):
    if "news" not in search_term:
        search_term=search_term+" stock news"
    
    url=f"https://www.google.com/search?q={search_term}&tbm=nws"
    url=re.sub(r"\s","+",url)
    return url

from bs4 import BeautifulSoup
def get_recent_stock_news(company_name):
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    g_query=google_query(company_name)
    res=requests.get(g_query,headers=headers).text
    soup=BeautifulSoup(res,"html.parser")
    news=[]
    for n in soup.find_all("div","n0jPhd ynAwRc MBeuO nDgy9d"):
        news.append(n.text)
    for n in soup.find_all("div","n0jPhd ynAwRc tNxQIb nDgy9d"):
        news.append(n.text)
    for n in soup.find_all("div","IJl0Z"):
        news.append(n.text)

    if len(news)>11:
        news=news[:10]
    else:
        news=news
    news_string=""
    for i,n in enumerate(news):
        news_string+=f"{i}. {n}\n"
    top10_news="Recent News:\n\n"+news_string
    
    return top10_news

def stock_news_search(company_name):
    search=DuckDuckGoSearchRun()
    return search("Stock news about " + company_name)


# Get financial statements from Yahoo Finance
def get_financial_statements(ticker):
    # if "." in ticker:
    #     ticker=ticker.split(".")[0]
    # else:
    #     ticker=ticker
    
    print("@@@@@@yf-ticker: ", ticker)
    company = yf.Ticker(ticker.strip())
    print("@@@@@@yf-company: ", company)
    
    balance_sheet = company.balance_sheet
    if balance_sheet.shape[1]>=3:
        balance_sheet=balance_sheet.iloc[:,:3]    # Only captures last 3 years of data
    balance_sheet=balance_sheet.dropna(how="any")
    return balance_sheet


from langchain.agents import Tool

tools=[
    Tool(
        name="get stock ticker",
        func=get_stock_ticker,
        description="Get the company name and stock ticker. You should input the company name to it. If the company name is written in Korean, do not translate it. If there are no output, simply say “Sorry. I can’t advice financial recommendation because of lack of information.”."
    ),
    Tool(
        name="get stock price",
        func=get_stock_price,
        description="Use when you are asked to evaluate or analyze a stock. This will output historic share price data. You should input the the stock ticker from the result of 'get stock ticker' to it."
    ),
    Tool(
        name="get recent news",
        func=get_recent_stock_news,
        description="Use this tool to fetch recent company news. You should input company name to it."
    ),

    Tool(
        name="get financial statements",
        func=get_financial_statements,
        description="Use this to get financial statement of the company. With the help of this data companys historic performance can be evaluated. You should input stock ticker to it"
    ) 

]

template="""Human: You are a financial advisor, but you don't know recent news about the company at all. Give stock recommendations for now using given query based on following instructions. If you cannot find stock ticker from following tools, stop giving advice and simply say “I can’t advice because of lack of information”.
<instructions>
Answer the following questions as best you can using stock price, recent news, and financial statements. You have access to the following tools, and you must use every follwing tools:

{tools}

</instructions>

<steps>
Note- 
1) Use "get company ticker" tool to get the stock ticker. Output- stock ticker.
2) Use "get stock price" tool to gather stock price info. Output- Stock price
3) Use "get recent news" tool to search for company's recent news. Output- recent news
4) Use "get financial statements" tool to get company's historic financial performance data. Output- Financial statement
5) Analyze the stock based on gathered data(price data, recent news, and financial) and give detail analysis for investment choice. provide numbers and reasons to justify your answer. provide target price of next 6 months based on closing price on {today} from stock price data you gathered. Output- Detailed stock Analysis
</steps>

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do, you must follow steps mentioned above
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer should be written with detail explanation to the original input question using each aspect you gathered. 
If you cannot get all information, just say "I cannot give any advices because of lacking of information."
You should translate only the message in Final Answer to Korean, the others should be written in English. Don't translate anything else. Say "Final Answer" instead of "최종답변".
Question: {input}

Assistant:
{agent_scratchpad}

"""

from langchain.agents import AgentExecutor, create_react_agent 

def initializeAgent():
    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm=get_claude3(), tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        max_iterations=7,
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    return agent_executor

    
