import random
import string
import gzip
import base64
import uuid

import requests
import hashlib
from urllib.parse import urlencode

from bitcoinlib.wallets import Wallet
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction

class UniSat:

    testnet: bool = False
    ts: str | None = None # timestamp from the very first API Call, important for requests signing
    app_id: str = "1adcd7969603261753f1812c9461cd36" # app id is most likely hardcoded into app version
    front_version: str = "285" # yet another hardcoded value. almost sure will change with updates
    signature_magic: str = "deda5ddd2b3d84988b2cb0a207c4674e" # hardcoded value, to be renamed & investigated
    client_id: str # seems like just a random string, implemented in self.__get_client_id

    btc_private_key: str
    btc_address: str # address of owner
    
    btc_tx_fee: int

    user_agent: str
    proxy: str | None = None

    def __init__(self, btc_private_key: str, btc_wallet_address: str, btc_tx_fee: int, testnet: bool, user_agent: str, proxy: str = None):
        self.btc_private_key = btc_private_key
        self.btc_tx_fee = btc_tx_fee
        self.testnet = testnet
        self.btc_address = btc_wallet_address
        self.user_agent = user_agent
        self.proxy = proxy

        self.client_id = self.__get_client_id()
        self.ts = self.get_ts()


    def api_request_get(self, endpoint: str, headers: object, payload: object) -> object:
        url = f"{self.__get_base_url()}/{endpoint}"
        
        q = requests.get(url=url, headers=headers, params=payload)
        return q

    def api_request_post(self, endpoint: str, headers: object, payload: object) -> object:
        url = f"{self.__get_base_url()}/{endpoint}"
        
        q = requests.post(url=url, headers=headers, json=payload)

        return q

    def get_config(self):
        headers = self.__get_headers(endpoint='basic-v4/config', method='get', params={})
        q = self.api_request_get('basic-v4/config', headers=headers, payload={})
        
        try:
            data = q.json()
            return data
        except:
            print('error')
            return

    def get_login(self):
        headers = self.__get_headers(endpoint='basic-v4/base/preload', method='get', params={"address":self.btc_address})
        q = self.api_request_get('basic-v4/base/preload', headers=headers, payload={"address":self.btc_address})
        data = q.json()

        print(data)

    def inscribe_mint(self, tick: str, fee_rate: int, amount: int, sats_in_item: int = 546):
        filename = {"p":"brc-20","op":"mint","tick":tick,"amt":str(amount)}
        params = {
            "files": [
                {
                    "dataURL": f"data:text/plain;charset=utf-8;base64,{self.__encode_base64(str(filename))}",
                    "filename": filename
                }
            ],
            "receiver": self.btc_address,
            "feeRate": fee_rate,
            "outputValue": sats_in_item,
            "clientId": self.client_id
        }

        headers = self.__get_headers(endpoint='inscribe-v5/order/create', method='post', params=params)

        q = self.api_request_post(endpoint='inscribe-v5/order/create', headers=headers, payload=params)

        q_data = q.json()["data"]
        order_id = q_data["orderId"]
        pay_address = q_data["payAddress"]
        amount = q_data["amount"]

        print(order_id, pay_address, amount)
        print('sending btc')

        tx = self.__send_btc(destination=pay_address, amount=amount, fee=self.btc_tx_fee)
        
        print('done, tx id', tx)

    def rune_mint(self, rune_name: str, fee_rate: int, count: int, sats_in_item: int = 546):
        rune_data = self.__get_rune_info(rune_name=rune_name)

        if not rune_data["data"]:
            print(f'Rune {rune_name} does not exist')
            return

        params = {
            "receiver": self.btc_address,
            "feeRate": fee_rate,
            "outputValue": sats_in_item,
            "clientId": self.client_id,
            "runeId": rune_data["data"]["runeid"],
            "count": count
        }

        headers = self.__get_headers(endpoint='inscribe-v5/order/create/runes-mint', method='post', params=params)
        
        q = self.api_request_post(endpoint='inscribe-v5/order/create/runes-mint', headers=headers, payload=params)
        
        q_data = q.json()["data"]
        order_id = q_data["orderId"]
        pay_address = q_data["payAddress"]
        amount = q_data["amount"]
        
        print(order_id, pay_address, amount)
        print('sending btc')
        
        tx = self.__send_btc(destination=pay_address, amount=amount, fee=self.btc_tx_fee)
        
        print('done, tx id', tx)

    def get_ts(self) -> str:
        headers = self.__get_headers(endpoint='ts2', method="get", params={})
        
        q = self.api_request_get('ts2', headers=headers, payload={})
        
        data = q.json()
        ts = data["data"]["ts"]
        
        print('ts', ts)

        return ts
    
    def get_signature(self, endpoint: str, method: str, params: object, ) -> str:
        query = ""

        if params:
            query = f"/{endpoint}?{self.__encode_url_params(params)}\n\n{self.ts}@#?.#@{self.signature_magic}"
        else:
            query = f"/{endpoint}\n\n{self.ts}@#?.#@{self.signature_magic}"
        
        signature = hashlib.md5(query.encode("utf-8")).hexdigest()

        return signature

    def get_cf_token(self, sign: str) -> str:
        token_parts = [
        ''.join(random.choices(string.ascii_lowercase + string.digits, k=6)),
        sign[12:14],
        ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + "u",
        ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        ]
        cf_token = ''.join(token_parts)
        
        return cf_token

    def __encode_url_params(self, params: object) -> str:
        res = urlencode(params)

        if not res:
            return "undefined"
        
        return res
    
    def __get_base_url(self) -> str:
        if self.testnet:
            return "https://api-testnet.unisat.io"

        return "https://api.unisat.space"

    def __get_headers(self, endpoint: str, method: str, params: object) -> object:
        api_urls = self.__get_api_urls()
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": api_urls["Origin"],
            "Pragma": "no-cache",
            "Referer": api_urls["Referrer"],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": self.user_agent,
            "sec-ch-ua": "\"Chromium\";v=\"128\", \"Not;A=Brand\";v=\"24\", \"Google Chrome\";v=\"128\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "macOS",
            "Fetch-Mode": "no-cors",
            "Fetch-Site": "same-origin"
        }

        if self.ts:
            sign = self.get_signature(endpoint=endpoint, method=method, params=params)
            headers["cf-token"] = self.get_cf_token(sign=sign)
            headers["x-appid"] = str(self.app_id)
            headers["X-Sign"] = sign
            headers["X-Ts"] = str(self.ts)
        
        if self.testnet:
            headers["content-type"] = "application/json"
            headers["priority"] = 'u=1, i'
            headers["Fetch-Site"] = 'same-origin'
            headers["Sec-Fetch-Site"] = "same-site"

        if not self.testnet:
            headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
            headers["Host"] = api_urls["Host"]
            headers["Connetcion"] = "keep-alive"

        if not self.testnet and self.ts:
            headers["X-Front-Version"] = str(self.front_version)

        print(headers)
        return headers

    def __get_api_urls(self) -> object:
        urls = {}

        if self.testnet:
            urls["Referrer"] = "https://testnet.unisat.io/"
            urls["Origin"] = "https://testnet.unisat.io"
            urls["Host"] = "api-testnet.unisat.io"
        
        if not self.testnet:
            urls["Referrer"] = "https://unisat.io/"
            urls["Origin"] = "https://unisat.io"
            urls["Host"] = "api.unisat.space"

        return urls

    def __get_mint_tick(self, tick: str) -> str:
        hex_codes = [format(ord(char), '02x') for char in tick]
        result = ''.join(hex_codes)
    
        return result

    def __encode_base64(self, string: str) -> str:
        string_bytes = string.encode('utf-8')

        base64_bytes = base64.b64encode(string_bytes)

        base64_string = base64_bytes.decode('utf-8')

        return base64_string
    
    def __get_client_id(self) -> str:
        client_id = uuid.uuid4().hex[:16]
       
        return client_id
    
    def __get_rune_info(self, rune_name: str) -> object:
        headers = self.__get_headers(f'query-v4/runes/{rune_name}/info', 'get', {})
        q = self.api_request_get(f'query-v4/runes/{rune_name}/info', headers=headers, payload={})
        
        data = q.json()

        return data

    def __send_btc(self, destination: str, amount: int, fee: int) -> str:
        key = Key(self.btc_private_key, network="bitcoin")
        
        wallet = Wallet.create('temp_wallet', keys=key, network="bitcoin")
        
        wallet.scan()
        
        if wallet.balance() < amount + fee:
            raise ValueError("Not Enough BTC to send tx")
        
        t = wallet.send_to(to_address=destination, amount=amount, fee=fee)
        
        t.send()
        
        wallet.delete_wallet()

        tx_id = t.txid

        return tx_id
