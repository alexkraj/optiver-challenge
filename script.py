from optibook.synchronous_client import Exchange
import time
import matplotlib.pyplot as plt
import numpy as np
import logging
logger = logging.getLogger('client')
logger.setLevel('ERROR')

print("Setup was successful.")

e = Exchange()
a = e.connect()

time.sleep(30)

philips_a = 'PHILIPS_A'
philips_b = 'PHILIPS_B'

### Generally Creating Useful Functions for The Future ###

def my_position():
    # Returns all current positions with cash invested
    positions = e.get_positions_and_cash()
    for p in positions:
        print(p, positions[p])
        
my_position()

# Delete all outstanding orders
def delete_outstanding(instrument):
    outstanding = e.get_outstanding_orders(instrument)
    for o in outstanding.values():
        result = e.delete_order(instrument, order_id=o.order_id)
        print(f"Deleted order id {o.order_id}: {result}")
        
# See all your outstanding orders
def view_outstanding(instrument):
    outstanding = e.get_outstanding_orders(instrument)
    for o in outstanding.values():
        print(f"Outstanding order: order_id({o.order_id}), instrument_id({o.instrument_id}), price({o.price}), volume({o.volume}), side({o.side})")


def best_selling_price(instrument):
    book = e.get_last_price_book(instrument)
    best = book.bids[0].price
    return best

def best_buying_price(instrument):
    book = e.get_last_price_book(instrument)
    best = book.asks[0].price
    return best
    
def average_a(timesteps):
    # Returns all public tradeticks since the instantiation of the Exchange
    tradeticks = e.get_trade_tick_history(philips_a)
    prices = []
    for t in tradeticks[-timesteps:]:
        if t.price<100:
            prices.append(t.price)

    return np.mean(prices)

def average_b(timesteps):
    # Returns all public tradeticks since the instantiation of the Exchange
    tradeticks = e.get_trade_tick_history(philips_b)
    prices = []
    for t in tradeticks[-timesteps:]:
        if t.price<100:
            prices.append(t.price)

    return np.mean(prices)

def get_range_b(timesteps):
    tradeticks = e.get_trade_tick_history(philips_b)
    prices = []
    for t in tradeticks[-timesteps:]:
        if t.price<100:
            prices.append(t.price)
    return [np.percentile(prices, 99), np.mean(prices), np.percentile(prices, 1)]
    
def get_range_a(timesteps):
    tradeticks = e.get_trade_tick_history(philips_a)
    prices = []
    for t in tradeticks[-timesteps:]:
        if t.price<100:
            prices.append(t.price)
    return [np.percentile(prices, 99), np.mean(prices), np.percentile(prices, 1)]


### Our Strategy Follows Here ### 

#Rather than Focussing on Arbitrage we try to make the most of a market that hopefully fluctuates around a reasonnably fixed average. Given no real product we thought this would be accurate. 

#We create an array that is a weighted version of our current portfolio of shares. We then view the market relative to the average of our current position in order to make decisions

#To add to this we send A and B off in opposite directions. If the market oscillates (fingers crossed) we make money as it moves in both directions. 

#We think this should work and it does for good periods of time. It is susceptible to large and consistent changes to the market which unfortunately happened this morning!

#A large change in value can cause one end of the weightings to be left in the distance
    
#If we had more time we would look how to counter this and allow for longer time changes. 
    
#Here We  initiate the weighted averages
weighted_prices_a = [average_a(3)]

weighted_prices_b = [average_b(3)]


#We track how our pnl changes
start_pnl = e.get_pnl()
new_pnl = e.get_pnl()
#Timer to report pnl changes every 10 'actions'
timer = 0
#new_start_b = [average_b(20)]*10
#weighted_prices_b = new_start_b

while timer<2000:
    stats_a = get_range_a(10000)
    stats_b = get_range_b(10000)
    
    max_range_a = stats_a[0]-stats_a[1] #We scale our purchase volume over the range we expect a typical fluctuation to occur
    low_range_b = stats_b[1]-stats_b[2]
    
    book_a = e.get_last_price_book(philips_a) #Obtain current books each round
    book_b = e.get_last_price_book(philips_b)
    
    if len(book_a.asks)!=0 and len(book_a.bids)!=0:
        current_ask_a = book_a.asks[0].price
        current_bid_a = book_a.bids[0].price
    if len(book_b.asks)!=0 and len(book_b.bids)!=0:
        current_ask_b = book_b.asks[0].price
        current_bid_b = book_b.bids[0].price
    #print(current_ask)
    
    average = average_b(2000)
    #print(average)
    positions = e.get_positions_and_cash()
    volume_left_a = positions[philips_a]['volume'] #Obtain Current Positions
    volume_left_b = positions[philips_b]['volume']
    
        
    
    # SELLING A WHEN HIGH
    if current_bid_a>np.mean(weighted_prices_a) and volume_left_a>-200:
        price = current_bid_a
        volume = max(int(10*(current_bid_a-stats_a[1])/max_range_a),1) #Here we do the volume scaling
        buying_order = e.insert_order(philips_a, price=current_bid_a, volume=float(volume), side = 'ask', order_type = 'limit')
        print('Selling %s A at price %s ****** Expect to buy at %s'%(volume, current_bid_a, np.mean(weighted_prices_a)))
        updated_weights = [price]*volume
        weighted_prices_a = updated_weights + weighted_prices_a #The updating of the array is crucial so that we focus on profit
        time.sleep(1) #Stopping us from buying too quickly
        timer+=1
        
    
    # BUYING A WHEN LOW
    if current_ask_a<np.mean(weighted_prices_a) and volume_left_a<200:
        sell_volume = min(int(10*(np.mean(weighted_prices_a)-current_ask_a)*max_range_a), np.abs(volume_left_a))
        if sell_volume<1:
            sell_volume = 1
        selling_order = e.insert_order(philips_a, price=current_ask_a, volume=float(sell_volume), side='bid', order_type='limit')  
        print('Buying  %s A at price %s'%(sell_volume, str(current_ask_a)))
        updated_weights = [current_ask_a]*sell_volume #We update our weighted array to take into account the value of our new actions
        weighted_prices_a =  weighted_prices_a[int(sell_volume):] + updated_weights
        time.sleep(0.5)
        timer +=1
        
    # BUYING B WHEN LOW
    if current_ask_b<np.mean(weighted_prices_b) and volume_left_b<200:
        price = current_ask_b
        volume = max(int(10*((stats_b[1]-current_ask_b)/low_range_b)),1)
        buying_order = e.insert_order(philips_b, price=current_ask_b, volume=volume, side = 'bid', order_type = 'limit')
        print('Buying %s B at price %s ****** Expect to sell at %s'%(volume, current_ask_b, np.mean(weighted_prices_b)))
        updated_weights = [price]*volume
        weighted_prices_b = updated_weights + weighted_prices_b
        time.sleep(1)
        timer+=1
        
    
    # SELLING B WHEN HIGH
    if current_bid_b>np.mean(weighted_prices_b) and volume_left_b>-200:
        sell_volume = min(int(10*(current_bid_b-np.mean(weighted_prices_b)*low_range_b)), volume_left_b)
        if sell_volume<1:
            sell_volume = 1
        selling_order = e.insert_order(philips_b, price=current_bid_b, volume=sell_volume, side='ask', order_type='limit')  
        print('Selling %s B at price %s'%(sell_volume, str(current_bid_b)))
        updated_weights = [current_bid_a]*sell_volume
        weighted_prices_b = weighted_prices_b[sell_volume:] + updated_weights 
        time.sleep(0.5)
        timer +=1
          
    if timer%10==0:
#         weighted_prices_a.append(average_a(5)-0.2)  We thought about introducing biases if nothing is happening to encourage action
        weighted_prices_a =  weighted_prices_a
        
#         weighted_prices_b.append(average_b(5)+0.3)
        weighted_prices_b = weighted_prices_b
        print('New PNL : %s'%(str(e.get_pnl()-new_pnl)))
        new_pnl = e.get_pnl()
        print('Updated Weights A=%s B=%s'%(np.mean(weighted_prices_a), np.mean(weighted_prices_b)))
        
        #Simply printing current updates.
        timer+=1
    #time.sleep(0.01)
    
    
end_pnl = e.get_pnl()

print('Pnl of stategy = %s'%(str(end_pnl - start_pnl))) #Overall value after 2000 actions