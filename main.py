from infogen import generate_infographic
from newspaper import Article
from newspaper.article import ArticleException

def main():
    while True:
        url = input("Enter a news URL: ").strip()
        try:
            article = Article(url)
            article.download()
            article.parse()
            break
        except ArticleException:
            print("That link doesn't seem valid. Double-check and try again. If it's correct, the site might be blocking access.")
    
    request = input("Optionally, describe what you'd like or a goal for the infographic (or press Enter to skip): ").strip()
    generate_infographic(url, request if request else None)

if __name__ == "__main__":
    main()
