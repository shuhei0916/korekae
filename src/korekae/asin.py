"""AmazonのURLからASINを取り出す。"""


def extract_asin(url: str) -> str | None:
    return url.rsplit("/dp/", 1)[1]
