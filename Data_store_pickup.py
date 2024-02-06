import os
import datetime
# 데이타 저장관련
import pandas as pd
import sqlite3

import socket                                   # 파이썬 인터프리트가 현재 실행되고 있는 기계의 hostname을 스트링 형태로 return





# 저장함수
def data_store(store_time_var, Folder_Name_DB_Store, Global_Option_Item_Code, Up_CenterOption_Down, current_monthmall, center_index, output_call_option_data, output_put_option_data):
    # 딕셔너리 선언 / 저장준비
    if center_index != 0:
        option_store = {'time': [], 'option_price': [], 'call_run_price': [], 'call_vol_cnt': [], 'call_Delta': [],
                        'put_run_price': [], 'put_vol_cnt': [], 'put_Delta': [],
                        'future_s': [], 'k200_s': [], 'day_residue': []}
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        # year 폴더
        folder_name_year = current_monthmall[:4]
        is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
        if is_folder_year == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

        # db명
        db_name = Global_Option_Item_Code + '_' + current_monthmall + '.db'
        # 테이블명 설정
        table_name_today = datetime.datetime.today().strftime("%Y%m%d")
        # # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
        # current_time = datetime.datetime.now()
        # # print(current_time)
        # # print(current_time.time())
        # # index_text_time = current_time.toString('hh:mm')
        # store_time_var = current_time.time()
        for i in range(center_index - Up_CenterOption_Down, center_index + Up_CenterOption_Down + 1):
            option_store['time'].append(store_time_var)
            # 행사가
            option_store['option_price'].append(output_call_option_data['option_price'][i])
            # 콜 저장용
            option_store['call_run_price'].append(output_call_option_data['run_price'][i])
            option_store['call_vol_cnt'].append(output_call_option_data['vol_cnt'][i])
            option_store['call_Delta'].append(output_call_option_data['Delta'][i])
            # 풋 저장용
            option_store['put_run_price'].append(output_put_option_data['run_price'][i])
            option_store['put_vol_cnt'].append(output_put_option_data['vol_cnt'][i])
            option_store['put_Delta'].append(output_put_option_data['Delta'][i])
            # 선물 k200 잔존일
            option_store['future_s'].append(output_call_option_data['future_s'][i])
            option_store['k200_s'].append(output_call_option_data['k200_s'][i])
            option_store['day_residue'].append(output_call_option_data['day_residue'][i])

        # 저장
        df = pd.DataFrame(option_store,
                          columns=['option_price', 'call_run_price', 'call_vol_cnt', 'call_Delta',
                                   'put_run_price', 'put_vol_cnt', 'put_Delta',
                                   'future_s', 'k200_s', 'day_residue'],
                          index=option_store['time'])

        con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + db_name)
        df.to_sql(table_name_today, con, if_exists='append', index_label='time')
        # 'append'는 테이블이 존재하면 데이터만을 추가
        # index_label	인덱스 칼럼에 대한 라벨을 지정

# 저장함수
def data_store_for_mssql(store_time_var, Folder_Name_DB_Store, Global_Option_Item_Code, Up_CenterOption_Down, current_monthmall, center_index, output_call_option_data, output_put_option_data, table_name_today):
    # 딕셔너리 선언 / 저장준비
    if center_index != 0:
        option_store = {'time': [], 'option_price': [], 'call_run_price': [], 'call_vol_cnt': [], 'call_Delta': [],
                        'put_run_price': [], 'put_vol_cnt': [], 'put_Delta': [],
                        'future_s': [], 'k200_s': [], 'day_residue': []}
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        # year 폴더
        folder_name_year = current_monthmall[:4]
        is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
        if is_folder_year == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

        # db명
        db_name = Global_Option_Item_Code + '_' + current_monthmall + '.db'
        # 테이블명 설정
        # table_name_today = datetime.datetime.today().strftime("%Y%m%d")
        # # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
        # current_time = datetime.datetime.now()
        # # print(current_time)
        # # print(current_time.time())
        # # index_text_time = current_time.toString('hh:mm')
        # store_time_var = current_time.time()
        for i in range(len(output_call_option_data['option_price'])):
            option_store['time'].append(store_time_var)
            # 행사가
            option_store['option_price'].append(output_call_option_data['option_price'][i])
            # 콜 저장용
            option_store['call_run_price'].append(output_call_option_data['run_price'][i])
            option_store['call_vol_cnt'].append(output_call_option_data['vol_cnt'][i])
            option_store['call_Delta'].append(output_call_option_data['Delta'][i])
            # 풋 저장용
            option_store['put_run_price'].append(output_put_option_data['run_price'][i])
            option_store['put_vol_cnt'].append(output_put_option_data['vol_cnt'][i])
            option_store['put_Delta'].append(output_put_option_data['Delta'][i])
            # 선물 k200 잔존일
            option_store['future_s'].append(output_call_option_data['future_s'][i])
            option_store['k200_s'].append(output_call_option_data['k200_s'][i])
            option_store['day_residue'].append(output_call_option_data['day_residue'][i])

        # 저장
        df = pd.DataFrame(option_store,
                          columns=['option_price', 'call_run_price', 'call_vol_cnt', 'call_Delta',
                                   'put_run_price', 'put_vol_cnt', 'put_Delta',
                                   'future_s', 'k200_s', 'day_residue'],
                          index=option_store['time'])

        con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + db_name)
        df.to_sql(table_name_today, con, if_exists='append', index_label='time')
        # 'append'는 테이블이 존재하면 데이터만을 추가
        # index_label	인덱스 칼럼에 대한 라벨을 지정

# stock 저장함수
def stock_data_store(store_time_var, Folder_Name_DB_Store, db_name, deal_power_data):
    # 딕셔너리 선언 / 저장준비
    stock_store = {'time': [], 'stock_no': [], 'stock_name': [], 'run_price': [], 'vol_cnt': [], 'deal_power': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # year 폴더
    folder_name_year = datetime.datetime.today().strftime("%Y")
    is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    if is_folder_year == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name + '.db'
    # 테이블명 설정
    table_name = datetime.datetime.today().strftime("%Y%m%d")
    # # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    # current_time = datetime.datetime.now()
    # # print(current_time)
    # # print(current_time.time())
    # # index_text_time = current_time.toString('hh:mm')
    # store_time_var = current_time.time()
    # 체결강도 종목 리스트에 저장
    for i in range(len(deal_power_data['stock_no'])):
        stock_store['time'].append(store_time_var)
        stock_store['stock_no'].append(deal_power_data['stock_no'][i])
        stock_store['stock_name'].append(deal_power_data['stock_name'][i])
        stock_store['run_price'].append(deal_power_data['run_price'][i])
        stock_store['vol_cnt'].append(deal_power_data['vol_cnt'][i])
        stock_store['deal_power'].append(deal_power_data['deal_power'][i])

    # 저장
    df = pd.DataFrame(stock_store,
                      columns=['stock_no', 'stock_name', 'run_price', 'vol_cnt', 'deal_power'],
                      index=stock_store['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정
	
def k200_total_data_store(store_time_var, Folder_Name_DB_Store, db_name_k200_total, stock_output_total_data):
    # 딕셔너리 선언 / 저장준비
    stock_store = {'time': [], 'stock_no': [], 'stock_name': [], 'run_price': [], 'stock_delta': [], 'k200_s': [],
                   'k200_s_delta': [], 'ref_up_cnt': [], 'k200_delta_ave': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # year 폴더
    folder_name_year = datetime.datetime.today().strftime("%Y")
    is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    if is_folder_year == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name_k200_total + '.db'
    # 테이블명 설정
    table_name = datetime.datetime.today().strftime("%Y%m%d")
    # # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    # current_time = datetime.datetime.now()
    # # print(current_time)
    # # print(current_time.time())
    # # index_text_time = current_time.toString('hh:mm')
    # store_time_var = current_time.time()
    # 체결강도 종목 리스트에 저장
    for i in range(len(stock_output_total_data['stock_no'])):
        stock_store['time'].append(store_time_var)
        stock_store['stock_no'].append(stock_output_total_data['stock_no'][i])
        stock_store['stock_name'].append(stock_output_total_data['stock_name'][i])
        stock_store['run_price'].append(stock_output_total_data['run_price'][i])
        stock_store['stock_delta'].append(stock_output_total_data['stock_delta'][i])
        stock_store['k200_s'].append(stock_output_total_data['k200_s'][i])
        stock_store['k200_s_delta'].append(stock_output_total_data['k200_s_delta'][i])
        stock_store['ref_up_cnt'].append(stock_output_total_data['ref_up_cnt'][i])
        stock_store['k200_delta_ave'].append(stock_output_total_data['k200_delta_ave'][i])

# 저장
    df = pd.DataFrame(stock_store,
                      columns=['stock_no', 'stock_name', 'run_price', 'stock_delta', 'k200_s', 'k200_s_delta',
                               'ref_up_cnt', 'k200_delta_ave'],
                      index=stock_store['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정

def stock_have_data_store(Folder_Name_DB_Store, db_name_stock_have_data, stock_have_data):
    # 딕셔너리 선언 / 저장준비
    stock_store = {'time': [], 'stock_no': [], 'stock_name': [], 'market_in_price': [], 'myhave_cnt': [], 'run_price': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # # year 폴더
    # folder_name_year = datetime.datetime.today().strftime("%Y")
    # is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    # if is_folder_year == False:
    #     os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name_stock_have_data + '.db'
    # 테이블명 설정
    table_name = datetime.datetime.today().strftime("%Y%m%d")
    # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    current_time = datetime.datetime.now()
    # print(current_time)
    # print(current_time.time())
    # index_text_time = current_time.toString('hh:mm')
    store_time_var = current_time.time()
    # 체결강도 종목 리스트에 저장
    for i in range(len(stock_have_data['stock_no'])):
        stock_store['time'].append(store_time_var)
        stock_store['stock_no'].append(stock_have_data['stock_no'][i])
        stock_store['stock_name'].append(stock_have_data['stock_name'][i])
        stock_store['market_in_price'].append(stock_have_data['market_in_price'][i])
        stock_store['myhave_cnt'].append(stock_have_data['myhave_cnt'][i])
        stock_store['run_price'].append(stock_have_data['run_price'][i])

# 저장
    df = pd.DataFrame(stock_store,
                      columns=['stock_no', 'stock_name', 'market_in_price', 'myhave_cnt', 'run_price'],
                      index=stock_store['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정

# 중심가 변경시 현황 저장
def center_option_s_change_data_store(Folder_Name_DB_Store, db_name_center_option_s_change_data, center_option_s_change_data):
    # 딕셔너리 선언 / 저장준비
    store_data = {'time': [], 'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'option_s_point_sum': [], 'option_s_point_in': [], 'option_s_point_myhave': [], 'day_residue_int': [], 'my_total_money': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # # year 폴더
    # folder_name_year = datetime.datetime.today().strftime("%Y")
    # is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    # if is_folder_year == False:
    #     os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name_center_option_s_change_data + '.db'
    # 테이블명 설정
    table_name = 'center_option_s_change_state'
    y_m_d_str = datetime.datetime.today().strftime("%Y%m%d")
    # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    current_time = datetime.datetime.now()
    # print(current_time)
    # print(current_time.time())
    now_time_str = current_time.time().strftime("%H%M")
    store_time_var = y_m_d_str + ' ' + now_time_str
    # center_option_s_change_data
    for i in range(len(center_option_s_change_data['center_option_price'])):
        store_data['time'].append(store_time_var)
        store_data['center_option_price'].append(center_option_s_change_data['center_option_price'][i])
        store_data['fu_run_price'].append(center_option_s_change_data['fu_run_price'][i])
        store_data['sell_or_buy'].append(center_option_s_change_data['sell_or_buy'][i])
        store_data['myhave_fu_cnt'].append(center_option_s_change_data['myhave_fu_cnt'][i])
        store_data['basket_cnt'].append(center_option_s_change_data['basket_cnt'][i])
        store_data['option_s_point_sum'].append(center_option_s_change_data['option_s_point_sum'][i])
        store_data['option_s_point_in'].append(center_option_s_change_data['option_s_point_in'][i])
        store_data['option_s_point_myhave'].append(center_option_s_change_data['option_s_point_myhave'][i])
        store_data['day_residue_int'].append(center_option_s_change_data['day_residue_int'][i])
        store_data['my_total_money'].append(center_option_s_change_data['my_total_money'][i])

# 저장
    df = pd.DataFrame(store_data,
                      columns=['center_option_price', 'fu_run_price', 'sell_or_buy', 'myhave_fu_cnt', 'basket_cnt', 'option_s_point_sum', 'option_s_point_in', 'option_s_point_myhave', 'day_residue_int', 'my_total_money'],
                      index=store_data['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정

# # 지난 옵션 헤지 비율 db 저장
def option_s_hedge_ratio_data_store(Folder_Name_DB_Store, db_name_option_s_hedge_ratio_data, option_s_hedge_ratio_data):
    # 딕셔너리 선언 / 저장준비
    store_data = {'time': [], 'option_s_hedge_ratio': [], 'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'day_residue_int': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # # year 폴더
    # folder_name_year = datetime.datetime.today().strftime("%Y")
    # is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    # if is_folder_year == False:
    #     os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name_option_s_hedge_ratio_data + '.db'
    # 테이블명 설정
    current_year = datetime.datetime.today().strftime("%Y")
    current_today = datetime.datetime.today().strftime("%Y%m%d")
    table_name = current_today
    y_m_d_str = datetime.datetime.today().strftime("%Y%m%d")
    # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    current_time = datetime.datetime.now()
    # print(current_time)
    # print(current_time.time())
    now_time_str = current_time.time().strftime("%H%M")
    store_time_var = y_m_d_str + ' ' + now_time_str
    # center_option_s_change_data
    for i in range(len(option_s_hedge_ratio_data['option_s_hedge_ratio'])):
        store_data['time'].append(store_time_var)
        store_data['option_s_hedge_ratio'].append(option_s_hedge_ratio_data['option_s_hedge_ratio'][i])
        store_data['center_option_price'].append(option_s_hedge_ratio_data['center_option_price'][i])
        store_data['fu_run_price'].append(option_s_hedge_ratio_data['fu_run_price'][i])
        store_data['sell_or_buy'].append(option_s_hedge_ratio_data['sell_or_buy'][i])
        store_data['myhave_fu_cnt'].append(option_s_hedge_ratio_data['myhave_fu_cnt'][i])
        store_data['basket_cnt'].append(option_s_hedge_ratio_data['basket_cnt'][i])
        store_data['day_residue_int'].append(option_s_hedge_ratio_data['day_residue_int'][i])

# 저장
    df = pd.DataFrame(store_data,
                      columns=['option_s_hedge_ratio', 'center_option_price', 'fu_run_price', 'sell_or_buy', 'myhave_fu_cnt', 'basket_cnt', 'day_residue_int'],
                      index=store_data['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정
    # db닫기
    con.commit()
    con.close()

# 선물(진입/청산) 신호발생시 db 저장
def future_s_signal_out_data_store(Folder_Name_DB_Store, db_name_future_s_signal_out_data, future_s_signal_out_data):
    # 딕셔너리 선언 / 저장준비
    store_data = {'time': [], 'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'day_residue_int': [], 'signal_out': []}
    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)
    # # year 폴더
    # folder_name_year = datetime.datetime.today().strftime("%Y")
    # is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)
    # if is_folder_year == False:
    #     os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year)

    # db명
    db_name_db = db_name_future_s_signal_out_data + '.db'
    # 테이블명 설정
    table_name = 'future_s_signal_out_data'
    y_m_d_str = datetime.datetime.today().strftime("%Y%m%d")
    # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
    current_time = datetime.datetime.now()
    # print(current_time)
    # print(current_time.time())
    now_time_str = current_time.time().strftime("%H%M")
    store_time_var = y_m_d_str + ' ' + now_time_str
    # center_option_s_change_data
    for i in range(len(future_s_signal_out_data['center_option_price'])):
        store_data['time'].append(store_time_var)
        store_data['center_option_price'].append(future_s_signal_out_data['center_option_price'][i])
        store_data['fu_run_price'].append(future_s_signal_out_data['fu_run_price'][i])
        store_data['sell_or_buy'].append(future_s_signal_out_data['sell_or_buy'][i])
        store_data['myhave_fu_cnt'].append(future_s_signal_out_data['myhave_fu_cnt'][i])
        store_data['basket_cnt'].append(future_s_signal_out_data['basket_cnt'][i])
        store_data['day_residue_int'].append(future_s_signal_out_data['day_residue_int'][i])
        store_data['signal_out'].append(future_s_signal_out_data['signal_out'][i])

# 저장
    df = pd.DataFrame(store_data,
                      columns=['center_option_price', 'fu_run_price', 'sell_or_buy', 'myhave_fu_cnt', 'basket_cnt', 'day_residue_int', 'signal_out'],
                      index=store_data['time'])

    con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + db_name_db)
    df.to_sql(table_name, con, if_exists='append', index_label='time')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정
    # db닫기
    con.commit()
    con.close()

# 가저오기 함수
def data_pickup(db_name, table_name):
    con = sqlite3.connect(db_name)
    df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
    # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
    # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당

    # print(df_read)
    # df_read.info()

    # db닫기
    con.commit()
    con.close()

    return df_read

# txt_file 저장함수
def txt_file_store(Folder_Name_TXT_Store, Global_Option_Item_Code, day_residue_str, txt_row_data):
    # 딕셔너리 선언 / 저장준비

    # 폴더
    # db_store 폴더
    is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_TXT_Store)
    if is_store_folder == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_TXT_Store)
    # year 폴더
    folder_name_year = datetime.datetime.today().strftime("%Y")
    is_folder_year = os.path.isdir(os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + folder_name_year)
    if is_folder_year == False:
        os.mkdir(os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + folder_name_year)

    # file명
    file_name_today = datetime.datetime.today().strftime("%Y%m%d")

    # 파이썬 인터프리트가 현재 실행되고 있는 기계의 hostname을 스트링 형태로 return
    pc_host_name = socket.gethostname()
    pc_ip_address = socket.gethostbyname(pc_host_name)
    # print('현재 실행되고 있는 기계의 hostname / pc_ip_address')
    # print(pc_host_name)
    # print(pc_ip_address)

    f = open(os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + folder_name_year + '/' + Global_Option_Item_Code + "_" + file_name_today + "(" + day_residue_str + ")" + "_" + pc_host_name + ".txt", 'at', encoding='UTF8')
    txt_row_data_str = str(txt_row_data)
    print(txt_row_data_str)
    f.write(txt_row_data_str + '\n')
    f.close()

if __name__ == "__main__":
    pass