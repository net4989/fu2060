import os
import datetime
# 데이타 저장관련
import pandas as pd
import sqlite3
# 자체모듈
from Data_store_pickup import *

# 중심가 기준 위아래 몇칸을 뒤질까요?
Up_CenterOption_Down = 9
# db 저장폴더
Folder_Name_DB_Store = 'db_store'
# 폴더
Folder_Name_OLD_DB_Store = 'old_option_price_mssql'
Global_Option_Item_Code = 'K200'

# 종목코드 앞자리
Global_Option_Item_Code_var = 'K200_mssql'

# 폴더
# db_store 폴더
is_store_folder = os.path.isdir(Folder_Name_OLD_DB_Store)
if is_store_folder == False:
    pass

dir_list_monthmall_xls = os.listdir(Folder_Name_OLD_DB_Store)
# print(dir_list_monthmall_xls)
# db 파일 제거
dir_list_monthmall_xls_call = []
dir_list_monthmall_xls_put = []
each_monthmall_start_day = ['20160212', '20160311', '20160415', '20160513', '20160610', '20160715', '20160812', '20160909', '20161014', '20161111',
                            '20161209', '20170113', '20170210', '20170310', '20170414', '20170512', '20170609', '20170714', '20170811', '20170915', '20171013', '20171110',
                            '20171215', '20180112', '20180209', '20180309', '20180413', '20180511', '20180615', '20180713', '20180810', '20180914', '20181012', '20181109',
                            '20181214', '20190111']
for dir in dir_list_monthmall_xls:
    # 201811, 201812 월물은 6만5천건 보다 많아서 xlsx로 저장함
    if (dir.endswith('call.xls')) or (dir.endswith('call.xlsx')):
        dir_list_monthmall_xls_call.append(dir)
    elif (dir.endswith('put.xls')) or (dir.endswith('put.xlsx')):
        dir_list_monthmall_xls_put.append(dir)

print(len(dir_list_monthmall_xls_call))
print(len(dir_list_monthmall_xls_put))
print(dir_list_monthmall_xls_call)
print(dir_list_monthmall_xls_put)

# xls_data_call = pd.read_excel('./' + Folder_Name_OLD_DB_Store + '/' + '201603_call.xls', header=None)
# print(xls_data_call.shape[0])
# dir_list_monthmall_xls_call = ['201604_call.xls']
# dir_list_monthmall_xls_put = ['201604_put.xls']

for i in range(len(dir_list_monthmall_xls_call)):
    xls_data_call = pd.read_excel('./' + Folder_Name_OLD_DB_Store + '/' + dir_list_monthmall_xls_call[i], header=None)
    xls_data_put = pd.read_excel('./' + Folder_Name_OLD_DB_Store + '/' + dir_list_monthmall_xls_put[i], header=None)

    for row in range(xls_data_call.shape[0]):
        atm_type = xls_data_call.at[row, 11]
        if atm_type == 1:
            center_index = row
            print(center_index)

            # 저장시간 만들기
            store_month_str = str(xls_data_call.at[row, 4])
            if len(store_month_str) == 1:
                store_month = '0' + store_month_str
            elif len(store_month_str) == 2:
                store_month = store_month_str

            store_day_str = str(xls_data_call.at[row, 5])
            if len(store_day_str) == 1:
                store_day = '0' + store_day_str
            elif len(store_day_str) == 2:
                store_day = store_day_str

            store_hour_str = str(xls_data_call.at[row, 6])
            if len(store_hour_str) == 1:
                store_hour = '0' + store_hour_str
            elif len(store_hour_str) == 2:
                store_hour = store_hour_str

            store_minu_str = str(xls_data_call.at[row, 7])
            if len(store_minu_str) == 1:
                store_minu = '0' + store_minu_str
            elif len(store_minu_str) == 2:
                store_minu = store_minu_str

            store_time_var = store_hour + ':' + store_minu
            print(store_time_var)
            table_name_today = str(xls_data_call.at[row, 3]) + store_month + store_day
            print(table_name_today)
            # 당월물만 저장하기 위하여
            if table_name_today < each_monthmall_start_day[i]:
                continue

            output_call_option_data = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                            'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                            'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                            'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}
            output_put_option_data = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                           'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                           'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                           'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}

            for p in range(center_index - Up_CenterOption_Down, center_index + Up_CenterOption_Down + 1):
                # output_call_option_data['time'].append(store_time_var)
                # 행사가
                output_call_option_data['option_price'].append(str(xls_data_call.at[p, 12]))
                # 콜 저장용
                output_call_option_data['run_price'].append(abs(float(xls_data_call.at[p, 13])))
                output_call_option_data['vol_cnt'].append(abs(int(xls_data_call.at[p, 20])))
                output_call_option_data['Delta'].append(abs(float(xls_data_call.at[p, 24])))
                # 풋 저장용
                output_put_option_data['run_price'].append(abs(float(xls_data_put.at[p, 13])))
                output_put_option_data['vol_cnt'].append(abs(int(xls_data_put.at[p, 20])))
                output_put_option_data['Delta'].append(abs(float(xls_data_put.at[p, 24])))
                # 선물 k200 잔존일
                output_call_option_data['future_s'].append(abs(float(xls_data_call.at[p, 9])))
                output_call_option_data['k200_s'].append(abs(float(xls_data_call.at[p, 8])))
                output_call_option_data['day_residue'].append(abs(int(0)))

            print(output_call_option_data)
            print(output_put_option_data)

            # db저장
            # db명 설정
            current_monthmall = str(xls_data_call.at[row, 2])
            print(current_monthmall)
            data_store_for_mssql(store_time_var, Folder_Name_DB_Store, Global_Option_Item_Code_var, Up_CenterOption_Down, current_monthmall, center_index, output_call_option_data, output_put_option_data, table_name_today)



