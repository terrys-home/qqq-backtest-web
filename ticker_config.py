"""티커 중앙관리 파일."""
TICKER_LIST = ["QQQ","TQQQ","SOXX","SOXL","TECL","FAS","USD","NVDL","TSLL","SNXX"]
def ticker_dict():
    return {ticker: ticker for ticker in TICKER_LIST}
