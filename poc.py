from UniSat import UniSat

private_key = ""
address = ""
proxy = ""
user_agent = ""

tx_fee = 7

us = UniSat(
    testnet=True, 
    btc_private_key=private_key, 
    btc_wallet_address=address, 
    btc_tx_fee=tx_fee, 
    user_agent=user_agent, 
    proxy=proxy)

us.get_config()

us.inscribe_mint(tick='zzzz', fee_rate=tx_fee, amount=1)

us.rune_mint(rune_name="THE•DAO•GATE•COIN", fee_rate=tx_fee, count=1)
