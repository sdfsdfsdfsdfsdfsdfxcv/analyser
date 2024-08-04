import os
import telebot
import pandas as pd
from binance.client import Client
import ta
import logging
from datetime import datetime
from persiantools.jdatetime import JalaliDateTime

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Binance client
binance_client = Client()

# Initialize Telegram bot
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "7474610426:AAEZfSWiMImUomZGWLE_gQuxUAQM49YXUDQ")
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', "-1002222040175")
bot = telebot.TeleBot(BOT_TOKEN)

CHANNEL_NAME = "Whale Room"

def get_bitcoin_data():
    logging.info("Fetching Bitcoin data from Binance")
    try:
        klines = binance_client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_4HOUR, "30 days ago UTC")
        
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        
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
        analysis.append(f"📊 قیمت در 4 ساعت گذشته {'افزایش' if price_change > 0 else 'کاهش'} یافته است به میزان {abs(price_change):.2f}٪.")
        
        if last_row['close'] > last_row['MA20'] > last_row['MA50']:
            analysis.append("📈 قیمت بالاتر از MA20 و MA50 است، که نشان‌دهنده روند صعودی قوی است.")
        elif last_row['close'] < last_row['MA20'] < last_row['MA50']:
            analysis.append("📉 قیمت پایین‌تر از MA20 و MA50 است، که نشان‌دهنده روند نزولی قوی است.")
        else:
            analysis.append("↔️ قیمت بین MA20 و MA50 است، که نشان‌دهنده احتمال تغییر روند یا تثبیت است.")
        
        if last_row['RSI'] > 70:
            analysis.append("🔥 مقدار RSI بالای 70 است، که نشان‌دهنده شرایط اشباع خرید است.")
        elif last_row['RSI'] < 30:
            analysis.append("❄️ مقدار RSI زیر 30 است، که نشان‌دهنده شرایط اشباع فروش است.")
        else:
            analysis.append(f"➖ مقدار RSI در سطح {last_row['RSI']:.2f} است، که نشان‌دهنده مومنتوم خنثی است.")
        
        if last_row['MACD'] > last_row['MACD_signal']:
            analysis.append("🐂 مقدار MACD بالای خط سیگنال است، که نشان‌دهنده مومنتوم صعودی است.")
        else:
            analysis.append("🐻 مقدار MACD زیر خط سیگنال است، که نشان‌دهنده مومنتوم نزولی است.")
        
        logging.info("Indicator analysis completed")
        return "\n".join(analysis)
    except Exception as e:
        logging.error(f"Error analyzing indicators: {str(e)}")
        raise

def send_analysis_to_telegram(analysis):
    logging.info("Sending analysis to Telegram")
    try:
        current_time = JalaliDateTime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"تحلیل تکنیکال بیت‌کوین برای {CHANNEL_NAME} 🚀\n\nزمان تحلیل: {current_time}\n\n{analysis}\n\n🐳 @WhaleRoomTrade"
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