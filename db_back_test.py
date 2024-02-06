import time
import datetime
from PyQt5 import uic

# 데이타 저장관련
import pandas as pd
import sqlite3
# 차트그리기
import matplotlib.pyplot as plt
# matplotlib를 이용해 PyQt 내에 그래프를 그리려면 FigureCanvasQTAgg 클래스를 사용
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 자체모듈
from Api_server_rq import *
from Cross_check import *
from Delta_check import *
from Layout_ui_chart import *
from Data_store_pickup import *



# db 저장폴더
Folder_Name_DB_Store = 'db_store'
Global_Option_Item_Code = 'K200'

# 1틱단계
One_Tick_Step = 0.01
# 기조자산 범위
Basic_Property_Range = 2.5










class DB_back_test:
    def __init__(self, monthmall):
        # 생성자
        self.monthmall = monthmall

    # 가져오기 함수
    def data_pickup_ready(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(Folder_Name_DB_Store)
        if is_store_folder == False:
            return

        self.select_monthmall()

    def select_monthmall(self):
        # 폴더
        current_year = self.monthmall[:4]
        # print(current_year)
        dir_list_monthmall = os.listdir(Folder_Name_DB_Store + '/' + current_year)
        # print(dir_list_monthmall)

        # 중간 텍스트 버리기
        only_monthmall = []
        for i in dir_list_monthmall:
            if (i.startswith(Global_Option_Item_Code)) and (i.endswith('.db')):

                if self.monthmall == (i[-9:-3]):
                    only_monthmall.append(i[5:-3])
        # 여러 기초자산으로 운용계획이므로 혹시 선택한 db 없을때는 리턴
        if len(only_monthmall) == 0:
            return

        self.comboBox_monthmall = only_monthmall

        self.select_date()

    def select_date(self):
        # 폴더
        folder_name_year = self.monthmall[:4]
        # 딕셔너리 선언 / pickup 준비
        db_option_pickup = {'date': [], 'time': [], 'option_price': [], 'call_run_price': [], 'put_run_price': [],
                            'future_s': [], 'k200_s': [], 'day_residue': []}
        # 리스트 만들고
        date_str_labels = []

        for db_name_end in self.comboBox_monthmall:
            # db명 설정
            db_name = Folder_Name_DB_Store + '/' + folder_name_year + '/' + Global_Option_Item_Code + '_' + db_name_end + '.db'
            # print(db_name)

            # 테이블명 가져오기
            con = sqlite3.connect(db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name = cursor.fetchall()
            con.close()

            for cell_table_name in total_table_name:
                # 데이타 가져오기 함수 호출
                data_pickup_ret = data_pickup(db_name, cell_table_name[0])

                # 날자 중복제거 저장
                if len(date_str_labels) == 0:
                    date_str_labels.append(cell_table_name[0])
                elif len(date_str_labels) >= 1:
                    same_date = cell_table_name[0] in date_str_labels
                    if same_date == False:
                        date_str_labels.append(cell_table_name[0])
                # 가져온 데이타 디셔너리 저장
                for b in range(len(data_pickup_ret)):
                    db_option_pickup['date'].append(cell_table_name[0])
                    db_option_pickup['time'].append(data_pickup_ret['time'][b])
                    db_option_pickup['option_price'].append(data_pickup_ret['option_price'][b])
                    db_option_pickup['call_run_price'].append(data_pickup_ret['call_run_price'][b])
                    db_option_pickup['put_run_price'].append(data_pickup_ret['put_run_price'][b])
                    db_option_pickup['future_s'].append(data_pickup_ret['future_s'][b])
                    db_option_pickup['k200_s'].append(data_pickup_ret['k200_s'][b])
                    db_option_pickup['day_residue'].append(data_pickup_ret['day_residue'][b])
        # 날자정렬
        date_str_labels.sort()
        # 시간 저장
        # 중심가 저장
        # 리스트 만들고
        time_str_labels = []
        center_str_labels = []
        for i in range(9, len(db_option_pickup['time']), 19):
            time_str_labels.append(db_option_pickup['time'][i])
            center_str_labels.append(db_option_pickup['option_price'][i])
        # 중심가 기준 아래꺼
        for step in range(9, 19):
            # 날자 돌림
            for d in range(len(date_str_labels)):
                # 변화량 작업시작
                self.change_work_start(db_option_pickup, date_str_labels[d], time_str_labels, center_str_labels, step)

    # 변화량 작업시작
    def change_work_start(self, db_option_pickup, date_str_labels, time_str_labels, center_str_labels, step):
        # 딕셔너리 선언
        option_back_test_data = {'monthmall': [], 'cross_market_in_date': [], 'cross_market_in_time': [],
                               'cross_ret': [], 'center_price': [],
                               'k200_s_in': [], 'call_price_in': [], 'put_price_in': [], 'day_residue': [],
                               'up_down_market_out_date': [], 'up_down_market_out_time': [],
                               'k200_s_out': [], 'call_price_out': [], 'put_price_out': [],
                               'k200_s_diff': [], 'call_price_diff': [], 'put_price_diff': [],
                               'call_delta': [], 'put_delta': []}

        # 기초자산 간격이 얼마로 나뉘는가? (기초자산의 범위 / 1틱단계)
        basic_step = Basic_Property_Range / One_Tick_Step
        # print(basic_step)
        # 만기날 가격 구해보기(중심가 기준으로 상하 간격의 차와 동일할것으로 예상) - 행사 못되는 놈을 0으로 가정하고
        endingday_price = basic_step / 2 * One_Tick_Step
        # print(endingday_price)
        # 매수진입가격 얼마 이상 첫번째 놈으로 잡을까 - 엔딩가격의 1/2 (행사가까지 가므로)
        Buy_MarketIn_Price_First = endingday_price / 2
        # print(Buy_MarketIn_Price_First)
        Buy_MarketIn_Price_First_half = Buy_MarketIn_Price_First / 2

        k200_s_list = []
        # 콜 / 풋 현재가 변화 리스트
        call_run_price_list = []
        put_run_price_list = []
        # 상대방 콜 현재가 구하기
        step_diff = step - 9
        # for d in range(len(date_str_labels)):
        for t in range(len(time_str_labels)):
            for b in range(len(db_option_pickup['time'])):
                # k200 제로이면 통과
                if db_option_pickup['k200_s'][b] == 0:
                    continue
                # 날자비교 / 시간비교 / 중심가비교
                if date_str_labels == db_option_pickup['date'][b]:
                    if time_str_labels[t] == db_option_pickup['time'][b]:
                        if center_str_labels[t] == db_option_pickup['option_price'][b]:
                            if db_option_pickup['put_run_price'][b + step_diff] > Buy_MarketIn_Price_First:
                                # k200_s_list append
                                if len(k200_s_list) == 0:
                                    k200_s_list.append(db_option_pickup['k200_s'][b])
                                # 중심가 append
                                if len(call_run_price_list) == 0 and (len(put_run_price_list) == 0):
                                    call_run_price_list.append(db_option_pickup['call_run_price'][b - step_diff])
                                    put_run_price_list.append(db_option_pickup['put_run_price'][b + step_diff])
                                # 중심가 다르면
                                elif center_str_labels[t] != center_str_labels[t - 1]:
                                    # Shift
                                    for i in range(b - 10, b - 10 - 19, -1):
                                        if center_str_labels[t] == db_option_pickup['option_price'][i]:
                                            # 콜 / 풋 현재가 변화 리스트
                                            call_run_price_list[0] = db_option_pickup['call_run_price'][i - step_diff]
                                            put_run_price_list[0] = db_option_pickup['put_run_price'][i + step_diff]
                                # 중심가 append
                                call_run_price_list.append(db_option_pickup['call_run_price'][b - step_diff])
                                put_run_price_list.append(db_option_pickup['put_run_price'][b + step_diff])
                                # cross_check_trans
                                cross = Cross(call_run_price_list, put_run_price_list)
                                cross_check_ret = cross.cross_check()
                                if cross_check_ret != None:
                                    # 교차 있으며 첫번째 삭제
                                    del call_run_price_list[-2]
                                    del put_run_price_list[-2]
                                    # 교차확인
                                    # 동일날자 교차만 인정
                                    if db_option_pickup['date'][b] == db_option_pickup['date'][b - 19]:
                                        # 동일중심가만 인정
                                        if center_str_labels[t] == db_option_pickup['option_price'][b - 19]:
                                            # 선물변화 확인
                                            if len(k200_s_list) >= 1:
                                                # k200_s_list.append
                                                k200_s_list.append(db_option_pickup['k200_s'][b])
                                                # K200 변화 퍼센트(1.001 / 0.999 - 0.1% , 1.0008 / 0.9992 - 0.1%의 80%, 1.0005 / 0.9995 - 0.1%의 50%)
                                                # K200 변화 (0.1%이상)
                                                future_s_percent_high = 1.001
                                                future_s_percent_low = 0.999
                                                if ((k200_s_list[-2] > (k200_s_list[-1] * future_s_percent_high)) or (
                                                        k200_s_list[-2] < (k200_s_list[-1] * future_s_percent_low))):
                                                    # 변화 오케
                                                    del k200_s_list[-2]
                                                    # k200s_change = Change_1per
                                                    k200s_change = Change_1per(b, db_option_pickup, k200_s_list, center_str_labels[t], step_diff)
                                                    k200s_change_call_put = k200s_change.change_1per_fn()
                                                    if k200s_change_call_put != None:

                                                        print('# cross_check_trans')
                                                        print(cross_check_ret)

                                                        print(db_option_pickup['date'][b])
                                                        print(db_option_pickup['time'][b])
                                                        print(center_str_labels[t])
                                                        print(db_option_pickup['k200_s'][b])

                                                        print(db_option_pickup['call_run_price'][b - step_diff])
                                                        print(db_option_pickup['put_run_price'][b + step_diff])

                                                        print(db_option_pickup['day_residue'][b])

                                                        print(k200s_change_call_put)
                                                        print(k200s_change_call_put[0])
                                                        print(k200s_change_call_put[1])
                                                        print(k200s_change_call_put[2])
                                                        print(k200s_change_call_put[3])
                                                        print(k200s_change_call_put[4])

                                                        print(' ')

                                                        monthmall = self.monthmall
                                                        cross_market_in_date = db_option_pickup['date'][b]
                                                        cross_market_in_time = db_option_pickup['time'][b]
                                                        cross_ret = cross_check_ret
                                                        center_price = center_str_labels[t]
                                                        k200_s_in = db_option_pickup['k200_s'][b]
                                                        call_price_in = db_option_pickup['call_run_price'][b - step_diff]
                                                        put_price_in = db_option_pickup['put_run_price'][b + step_diff]
                                                        day_residue = db_option_pickup['day_residue'][b]
                                                        up_down_market_out_date = k200s_change_call_put[0]
                                                        up_down_market_out_time = k200s_change_call_put[1]
                                                        k200_s_out = k200s_change_call_put[2]
                                                        call_price_out = k200s_change_call_put[3]
                                                        put_price_out = k200s_change_call_put[4]
                                                        k200_s_diff = ((k200_s_out - k200_s_in) / k200_s_in) * 100
                                                        call_price_diff = call_price_out - call_price_in
                                                        put_price_diff = put_price_out - put_price_in
                                                        call_delta = (call_price_diff / k200_s_diff) * 100
                                                        put_delta = (put_price_diff / k200_s_diff) * 100

                                                        # 딕셔너리
                                                        option_back_test_data['monthmall'].append(monthmall)
                                                        option_back_test_data['cross_market_in_date'].append(cross_market_in_date)
                                                        option_back_test_data['cross_market_in_time'].append(cross_market_in_time)
                                                        option_back_test_data['cross_ret'].append(cross_ret)
                                                        option_back_test_data['center_price'].append(center_price)
                                                        option_back_test_data['k200_s_in'].append(k200_s_in)
                                                        option_back_test_data['call_price_in'].append(call_price_in)
                                                        option_back_test_data['put_price_in'].append(put_price_in)
                                                        option_back_test_data['day_residue'].append(day_residue)
                                                        option_back_test_data['up_down_market_out_date'].append(up_down_market_out_date)
                                                        option_back_test_data['up_down_market_out_time'].append(up_down_market_out_time)
                                                        option_back_test_data['k200_s_out'].append(k200_s_out)
                                                        option_back_test_data['call_price_out'].append(call_price_out)
                                                        option_back_test_data['put_price_out'].append(put_price_out)
                                                        option_back_test_data['k200_s_diff'].append(k200_s_diff)
                                                        option_back_test_data['call_price_diff'].append(call_price_diff)
                                                        option_back_test_data['put_price_diff'].append(put_price_diff)
                                                        option_back_test_data['call_delta'].append(call_delta)
                                                        option_back_test_data['put_delta'].append(put_delta)
                                                # K200 변화 (0.1%이상)
                                                else:
                                                    del k200_s_list[-1]
                                # cross_check_trans
                                else:
                                    del call_run_price_list[-1]
                                    del put_run_price_list[-1]

        # db_name_option_back_test DB
        # db명 설정
        db_name_option_back_test = 'option_back_test'
        self.option_back_test_store(Folder_Name_DB_Store, db_name_option_back_test, option_back_test_data, step_diff)

    def option_back_test_store(self, Folder_Name_DB_Store, db_name_option_back_test, option_back_test_data, step_diff):
        # 딕셔너리 선언 / 저장준비
        stock_store = {'time': [], 'monthmall': [], 'cross_market_in_date': [], 'cross_market_in_time': [],
                       'step_diff': [], 'cross_ret': [], 'center_price': [],
                       'k200_s_in': [], 'call_price_in': [], 'put_price_in': [], 'day_residue': [],
                       'up_down_market_out_date': [], 'up_down_market_out_time': [],
                       'k200_s_out': [], 'call_price_out': [], 'put_price_out': [],
                       'k200_s_diff': [], 'call_price_diff': [], 'put_price_diff': [],
                       'call_delta': [], 'put_delta': []}
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
        db_name_db = db_name_option_back_test + '.db'
        # 테이블명 설정
        step_str = str(step_diff)
        # 년을 테이블로
        table_name_plus = self.monthmall[:4]
        # table_name_plus = 'back_test'
        table_name = table_name_plus
        # 시분초(인덱스)::time(): 시간 정보만 가지는 datetime.time 클래스 객체 반환
        current_time = datetime.datetime.now()
        # print(current_time)
        # print(current_time.time())
        # index_text_time = current_time.toString('hh:mm')
        store_time_var = current_time.time()
        # 체결강도 종목 리스트에 저장
        for i in range(len(option_back_test_data['monthmall'])):
            stock_store['time'].append(store_time_var)
            stock_store['monthmall'].append(option_back_test_data['monthmall'][i])
            stock_store['cross_market_in_date'].append(option_back_test_data['cross_market_in_date'][i])
            stock_store['cross_market_in_time'].append(option_back_test_data['cross_market_in_time'][i])
            stock_store['step_diff'].append(step_diff)
            stock_store['cross_ret'].append(option_back_test_data['cross_ret'][i])
            stock_store['center_price'].append(option_back_test_data['center_price'][i])
            stock_store['k200_s_in'].append(option_back_test_data['k200_s_in'][i])
            stock_store['call_price_in'].append(option_back_test_data['call_price_in'][i])
            stock_store['put_price_in'].append(option_back_test_data['put_price_in'][i])
            stock_store['day_residue'].append(option_back_test_data['day_residue'][i])
            stock_store['up_down_market_out_date'].append(option_back_test_data['up_down_market_out_date'][i])
            stock_store['up_down_market_out_time'].append(option_back_test_data['up_down_market_out_time'][i])
            stock_store['k200_s_out'].append(option_back_test_data['k200_s_out'][i])
            stock_store['call_price_out'].append(option_back_test_data['call_price_out'][i])
            stock_store['put_price_out'].append(option_back_test_data['put_price_out'][i])
            stock_store['k200_s_diff'].append(option_back_test_data['k200_s_diff'][i])
            stock_store['call_price_diff'].append(option_back_test_data['call_price_diff'][i])
            stock_store['put_price_diff'].append(option_back_test_data['put_price_diff'][i])
            stock_store['call_delta'].append(option_back_test_data['call_delta'][i])
            stock_store['put_delta'].append(option_back_test_data['put_delta'][i])

        # 저장
        df = pd.DataFrame(stock_store,
                          columns=['monthmall', 'cross_market_in_date', 'cross_market_in_time',
                                   'step_diff', 'cross_ret', 'center_price',
                                   'k200_s_in', 'call_price_in', 'put_price_in', 'day_residue',
                                   'up_down_market_out_date', 'up_down_market_out_time',
                                   'k200_s_out', 'call_price_out', 'put_price_out',
                                   'k200_s_diff', 'call_price_diff', 'put_price_diff',
                                   'call_delta', 'put_delta'],
                          index=stock_store['time'])

        con = sqlite3.connect(os.getcwd() + '/' + Folder_Name_DB_Store + '/' + db_name_db)
        df.to_sql(table_name, con, if_exists='append', index_label='time')
        # 'append'는 테이블이 존재하면 데이터만을 추가
        # index_label	인덱스 칼럼에 대한 라벨을 지정

class Change_1per:
    def __init__(self, b_start, db_option_pickup, k200_s_list, option_price, step_diff):
        self.b_start = b_start
        self.db_option_pickup = db_option_pickup
        self.k200_s_list = k200_s_list
        self.option_price = option_price
        self.step_diff = step_diff

    # 가져오기 함수
    def change_1per_fn(self):
        # 변화량 작업시작
        for b in range(self.b_start, len(self.db_option_pickup['time'])):
            # k200 제로이면 통과
            if self.db_option_pickup['k200_s'][b] == 0:
                continue
            # 보내온 중심가와 동일할때
            if self.option_price == self.db_option_pickup['option_price'][b]:
                # 선물변화 확인
                if len(self.k200_s_list) >= 1:
                    # self.k200_s_list.append
                    self.k200_s_list.append(self.db_option_pickup['k200_s'][b])
                    # K200 변화 퍼센트(1.001 / 0.999 - 0.1% , 1.0008 / 0.9992 - 0.1%의 80%, 1.0005 / 0.9995 - 0.1%의 50%)
                    # K200 변화 (1%이상)
                    future_s_percent_high = 1.01
                    future_s_percent_low = 0.99
                    if ((self.k200_s_list[-2] > (self.k200_s_list[-1] * future_s_percent_high)) or (
                            self.k200_s_list[-2] < (self.k200_s_list[-1] * future_s_percent_low))):
                        # 변화 오케
                        del self.k200_s_list[-2]
                        return self.db_option_pickup['date'][b], self.db_option_pickup['time'][b], \
                               self.db_option_pickup['k200_s'][b], \
                               self.db_option_pickup['call_run_price'][b - self.step_diff],\
                               self.db_option_pickup['put_run_price'][b + self.step_diff]
                    # K200 변화 (1%이상)
                    else:
                        del self.k200_s_list[-1]

if __name__ == "__main__":
    app = QApplication(sys.argv)

    all_monthmall = ['201911']
    for monthmall in all_monthmall:

    # monthmall = '201902'

        # back_test = DB_back_test
        back_test = DB_back_test(monthmall)
        back_test.data_pickup_ready()


