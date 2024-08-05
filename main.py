import os
import telebot
import pandas as pd
import ta
import logging
from datetime import datetime, timedelta
from persiantools.jdatetime import JalaliDateTime
import requests
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Telegram bot
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_NAME = "Whale Room"

def get_bitcoin_data():
    logging.info("Fetching Bitcoin data from BingX")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
        params = {
            "symbol": "BTC-USDT",
            "interval": "4h",  # Changed from "240" to "4h"
            "startTime": int(start_date.timestamp() * 1000),
            "endTime": int(end_date.timestamp() * 1000),
            "limit": 500  # Adjust as needed, max is 1000
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'code' in data and data['code'] != 0:
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")
        
        df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
        df.set_index('timestamp', inplace=True)
        
        logging.info(f"Successfully fetched {len(df)} data points")
        return df
    except Exception as e:
        logging.error(f"Error fetching Bitcoin data: {str(e)}")
        raise

def calculate_indicators(df):
    logging.info("Calculating technical indicators")
    try:
        df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        
        df['MA20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
        df['MA50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
        
        df['ATR'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
        
        logging.info("Technical indicators calculated successfully")
        return df
    except Exception as e:
        logging.error(f"Error calculating indicators: {str(e)}")
        raise

def analyze_indicators(df):
    logging.info("Analyzing indicators")
    try:
        last_row = df.iloc[-1]
        analysis = []
        
        price_change = (last_row['close'] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
        if price_change > 0:
            analysis.append(f"📈 واو! قیمت بیت‌کوین تو 4 ساعت گذشته {price_change:.2f}٪ رفته بالا! چه خبره؟")
        else:
            analysis.append(f"📉 اوه اوه! قیمت بیت‌کوین تو 4 ساعت گذشته {abs(price_change):.2f}٪ اومده پایین. نگران نباشید، این‌ها عادیه!")
        
        if last_row['close'] > last_row['MA20'] > last_row['MA50']:
            analysis.append("🚀 به به! قیمت از MA20 و MA50 زده بالاتر. انگار داره میره ماه!")
        elif last_row['close'] < last_row['MA20'] < last_row['MA50']:
            analysis.append("🐻 اوضاع یکم خرسی شده! قیمت زیر MA20 و MA50 هست. مواظب باشید!")
        else:
            analysis.append("🎢 قیمت بین MA20 و MA50 در نوسانه. انگار بیت‌کوین تصمیمش رو نگرفته کدوم وری بره!")
        
        if last_row['RSI'] > 70:
            analysis.append("🔥 مقدار RSI از 70 زده بالاتر! داغ داغه، ولی مواظب باش نسوزی!")
        elif last_row['RSI'] < 30:
            analysis.append("🧊 مقدار RSI رفته زیر 30! سرده سرده، ولی شاید وقت خرید باشه؟")
        else:
            analysis.append(f"😐 مقدار RSI الان {last_row['RSI']:.2f} هست. نه داغه، نه سرد. فعلاً خنثی میزنه.")
        
        if last_row['MACD'] > last_row['MACD_signal']:
            analysis.append("🐂 مقدار MACD از خط سیگنال زده بالاتر! گاوها دارن زور میزنن!")
        else:
            analysis.append("🐻 مقدار MACD زیر خط سیگناله! خرس‌ها دارن قدرت نمایی می‌کنن!")
        
        # Calculate probabilities
        rising_prob, falling_prob, ranging_prob = calculate_probabilities(df)
        analysis.append(f"\n🎰 بذار ببینم شانست چقدره:")
        analysis.append(f"📈 احتمال صعود: {rising_prob:.2f}٪")
        analysis.append(f"📉 احتمال نزول: {falling_prob:.2f}٪")
        analysis.append(f"↔️ احتمال نوسان: {ranging_prob:.2f}٪")
        
        # Add guidance
        guidance = provide_guidance(rising_prob, falling_prob, ranging_prob, last_row)
        analysis.append(f"\n💡 نظر من چیه؟ بذار بگم:")
        analysis.append(guidance)
        
        logging.info("Indicator analysis completed")
        return "\n".join(analysis)
    except Exception as e:
        logging.error(f"Error analyzing indicators: {str(e)}")
        raise

def calculate_probabilities(df):
    last_row = df.iloc[-1]
    
    # Trend based on moving averages
    trend_score = (1 if last_row['close'] > last_row['MA20'] else -1) + \
                  (1 if last_row['close'] > last_row['MA50'] else -1)
    
    # Momentum based on RSI and MACD
    momentum_score = (1 if last_row['RSI'] > 50 else -1) + \
                     (1 if last_row['MACD'] > last_row['MACD_signal'] else -1)
    
    # Volatility based on ATR
    volatility = last_row['ATR'] / last_row['close']
    
    # Calculate probabilities
    total_score = trend_score + momentum_score
    rising_prob = max(0, min(100, 50 + total_score * 12.5))
    falling_prob = max(0, min(100, 50 - total_score * 12.5))
    ranging_prob = max(0, 100 - rising_prob - falling_prob)
    
    # Adjust for volatility
    if volatility > 0.03:  # High volatility
        ranging_prob = min(ranging_prob, 20)
        excess = (100 - ranging_prob) / 2
        rising_prob = falling_prob = excess
    elif volatility < 0.01:  # Low volatility
        ranging_prob = max(ranging_prob, 60)
        excess = (100 - ranging_prob) / 2
        rising_prob = falling_prob = excess
    
    return rising_prob, falling_prob, ranging_prob

def provide_guidance(rising_prob, falling_prob, ranging_prob, last_row):
    guidance = []
    
    if rising_prob > max(falling_prob, ranging_prob):
        guidance.append("🚀 به نظر میاد بازار داره گرم میشه! اگه جای خوبی برای خرید پیدا کردی، شاید بد نباشه یه کم بخری.")
        if last_row['RSI'] > 70:
            guidance.append("🔥 ولی حواست باشه، RSI خیلی بالاست. یعنی ممکنه یهو برگرده پایین. مواظب باش!")
    elif falling_prob > max(rising_prob, ranging_prob):
        guidance.append("🛷 اوه اوه، انگار بازار داره سر میخوره! اگه جای خوبی برای فروش دیدی، شاید وقتشه یه کم سود بگیری.")
        if last_row['RSI'] < 30:
            guidance.append("🧊 البته RSI خیلی پایینه. یعنی ممکنه یهو برگرده بالا. حواست جمع باشه!")
    else:
        guidance.append("🎢 فعلاً بازار داره این ور و اون ور میره. شاید بهتره صبر کنی ببینی چی میشه. اگه دوست داری، میتونی تو این نوسان‌ها خرید و فروش کنی.")
    
    guidance.append("🧠 یادت نره، این فقط نظر منه! همیشه خودت فکر کن و تصمیم بگیر. مواظب سرمایه‌ات باش و ریسک نکن!")
    
    return "\n".join(guidance)

def send_analysis_to_telegram(analysis):
    logging.info("Sending analysis to Telegram")
    try:
        current_time = JalaliDateTime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"🔍 تحلیل بیت‌کوین برای {CHANNEL_NAME} 🚀\n\n⏰ زمان تحلیل: {current_time}\n\n{analysis}\n\n🐳 @WhaleRoomTrade"
        bot.send_message(CHANNEL_ID, message)
        logging.info("Analysis sent to Telegram successfully")
    except Exception as e:
        logging.error(f"Error sending analysis to Telegram: {str(e)}")
        raise

def main():
    logging.info("Starting Bitcoin analysis script")
    try:
        df = get_bitcoin_data()
        df = calculate_indicators(df)
        analysis = analyze_indicators(df)
        send_analysis_to_telegram(analysis)
        logging.info("Bitcoin analysis completed successfully")
    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
