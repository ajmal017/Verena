from quantopian.pipeline import Pipeline, CustomFilter
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.factors import Latest
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data.psychsignal import aggregated_twitter_withretweets_stocktwits as st
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.filters import Q1500US
import numpy as np

def initialize(context):
    print("Initializing")
    context.gap = 28 #default value
    context.oo = 0
    context.max_leverage = 0.0
    context.securities_in_results = []
    attach_pipeline(Custom_pipeline(context), 'Custom_pipeline') 
    
    # Schedule orders
    schedule_function(sell, date_rules.every_day(), time_rules.market_open()) #open sell orders
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close(minutes = 91)) 
    schedule_function(buy, date_rules.every_day(), time_rules.market_close(minutes = 90)) #open buy orders
    schedule_function(buy_2, date_rules.every_day(), time_rules.market_close(minutes = 30)) #open buy
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close(minutes = 31)) #close buy orders
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close())
    schedule_function(day_end,date_rules.every_day(), time_rules.market_close())
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=0.0))
    
    context.longs = []
    context.S = []
    context.B = []
    
    print("Initialization Successful")

class SidInList(CustomFilter):  
    inputs = []
    window_length = 1
    params = ('sid_list',)
    def compute(self, today, assets, out, sid_list):
        out[:] = np.in1d(assets, sid_list)
        
def day_end(context, data):
    for sec in context.portfolio.positions:
        log.info("Portfolio consists of: " + str(sec))
        
def Custom_pipeline(context):
    pipe = Pipeline()
    
    # Get bull/bearish data and sentiment data and store window length differences in different variables
    sma_bear_7 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=7)
    sma_bull_7 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=7)
    sma_bear_6 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=6)
    sma_bull_6 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=6)
    sma_bear_5 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=5)
    sma_bull_5 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=5)
    sma_bear_4 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=4)
    sma_bull_4 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=4)
    sma_bear_3 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=3)
    sma_bull_3 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=3)
    sma_bear_2 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=2)
    sma_bull_2 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=2)
    bull_1 = st.bullish_intensity.latest
    bear_1 = st.bearish_intensity.latest
    volume = USEquityPricing.volume
    pipe.add(st.bullish_intensity.latest, 'bullish_intensity')
    pipe.add(st.bearish_intensity.latest, 'bearish_intensity')
    pipe.add(st.total_scanned_messages.latest, 'total_scanned_messages') 
    
    total_scan = st.total_scanned_messages.latest
    pricing = USEquityPricing.close.latest
    
    # Conditionals for determining stocks to screen
    price_range = 1.00 < pricing < 12.50
    min_volume = volume > 4000000
    total_scans = total_scan >= 10
    bull_condition = bull_1 > sma_bull_2 < sma_bull_3 < sma_bull_4 < sma_bull_5 < sma_bull_6 > 0
    bull_latest = bull_1 > 0
    
    # Set stock screener
    pipe.set_screen(price_range & min_volume & total_scans & bull_condition & bull_latest)
    return pipe

def before_trading_start(context,data): 
    print("Prepping for trading...")
    context.B = []
    context.S = []
    context.results = pipeline_output('Custom_pipeline')
    context.securities_in_results = []
    
    context.longs = []
    for s in context.results.index:
        if data.can_trade(s):
            context.longs.append(s)
    
def sell (context, data):
    print("Closing positions...")
    PricingData = data.current(context.portfolio.positions.keys(),'price')
    for sec in context.portfolio.positions:
        if sec not in context.B:
            limit = PricingData[sec]
            try:
                order_target_percent(sec,0,style = LimitOrder(0.98*limit))
                context.S.append(sec)
            except:
                order_target_percent(sec,0)
                context.S.append(sec)
            
def buy (context, data): 
   
    context.results = pipeline_output('Custom_pipeline')
    context.securities_in_results = []
    
    for s in context.results.index:
        context.securities_in_results.append(s) 
    context.longs= []
    if len(context.securities_in_results) > 0.0:                    
        for sec in context.securities_in_results:
            if data.can_trade(sec):
                context.longs.append(sec)
    context.gap = 29 # after 60 minutes, close any open buy order. 
    count = 0
    for sec in context.portfolio.positions:
        if sec not in context.longs:
            count += 1

    #if len(context.longs) < 15:
    #    context.longs = []
    PricingData = data.current(context.longs,'price')
    for sec in context.longs:
        if sec not in context.S:
            limit = PricingData[sec]
            order_target_percent(sec, 0.99/len(context.longs), style = LimitOrder(limit) )
            context.B.append(sec)

def buy_2 (context, data):
    hold = []
    if len(context.portfolio.positions) >= 0:
    #if len(context.portfolio.positions) >= 15:
        for sec in context.portfolio.positions:
            hold.append(sec)
        PricingData = data.current(hold,'price')
        for sec in context.portfolio.positions:
            limit = PricingData[sec]
            try:
                order_target_percent(sec, 0.99/len(context.portfolio.positions), style = LimitOrder(limit) )
            except:
                pass
        
    
def kill_open_orders(context, data):  
    for sec, orders in get_open_orders().iteritems():  
        for oo in orders:  
            # log.info("X CANCELED {0:s} with {1:,d} / {2:,d} filled"\
            #          .format(sec.symbol,  oo.filled, oo.amount))  
            cancel_order(oo)  
    return

def has_orders(context, data):  
    # Return true if there are pending orders.  
    has_orders = False  
    for sec in context.longs:  
        orders = get_open_orders(sec)  
        if orders:  
            for oo in orders:  
                message = 'Open order for {amount} shares in {stock}'  
                message = message.format(amount=oo.amount, stock=sec)  
                log.info(message)
            has_orders = True  
    return has_orders  

def cancel_orders (context, data):
    while has_orders(context, data):  
        kill_open_orders(context, data)  
        print('Canceled orders - TicksOfOpenOrders= ', context.oo)  
        return  
    else:
        context.oo = 0
        
# Display and handle maximum leverage
def handle_data (context, data): 
    if context.account.leverage > context.max_leverage:
        context.max_leverage = context.account.leverage
    record(Leverage = context.account.leverage,
           pos=len(context.portfolio.positions),
           results=len(context.securities_in_results),
           max_leverage = context.max_leverage,
          )