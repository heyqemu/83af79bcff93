from UniSat import UniSat

private_key = ""
address = ""
proxy = ""
user_agent = ""

us = UniSat(
    testnet=True, 
    btc_private_key=private_key, 
    btc_wallet_address=address, 
    btc_tx_fee=50, 
    user_agent=user_agent, 
    proxy=proxy)

us.get_config()

us.inscribe_mint(tick='zzzz', fee_rate=5, amount=2)

us.rune_mint(rune_name="THE•DAO•GATE•COIN", fee_rate=5, count=2)
