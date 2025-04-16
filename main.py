from chatbot import run_bot
from newspaper import Article
from newspaper.article import ArticleException
import logging

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('./enh_news_info/app.log')
        ]
    )

    run_bot()

if __name__ == "__main__":
    main()
