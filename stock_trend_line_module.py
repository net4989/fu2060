# =====
# 라이브러리 사용
# import numpy as np
# Numpy를 사용하기 위해 import 해준다
# from matplotlib import pyplot as plt
# pyplot을 사용하기 위해 import 해준다.
# from sklearn.preprocessing import PolynomialFeatures
# PolynomialFeatures 함수를 사용하기 위해 import 해준다.
# from sklearn.linear_model import LinearRegression
# LinearRegression 함수를 사용하기 위해 import 해준다

import sys
import datetime
import sqlite3
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression


def stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt):
    # 디셔너리 변수 선언
    stock_trend_line_of_ai = {'stock_no': [],
                              'poly_sell_max_price': [], 'poly_buy_min_price': [],
                              'sell_max_price': [], 'buy_min_price': [],
                              'poly_h_gradient': [], 'poly_l_gradient': [], 'h_gradient': [], 'l_gradient': [],
                              'candle_cnt': [], 'text_time': []}

    # 시간표시
    current_time = datetime.datetime.now()
    text_time = current_time.strftime('%H:%M:%S')

    # 1. 데이터셋 생성하기
    # db 저장폴더

    # 테이블명 가져오기
    con = sqlite3.connect(db_file_path + '/' + get_db_name)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    total_table_name_of_db = cursor.fetchall()
    # print(total_table_name_of_db)
    # 실제 테이블 구하기
    total_table_name = []
    for table in total_table_name_of_db:
        total_table_name.append(table[0])
    # print(total_table_name)

    # total_table_name = ['000660']
    # 실행파일에서 인자 받아서 처리하기
    if len(sys.argv) > 1:
        print(sys.argv[0])  # 파일명
        print(sys.argv[1])  # 첫번째 인자
        total_table_name = [sys.argv[1]]
    # print(total_table_name)

    for table_name in total_table_name:
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()

        # pd 필요건수 만큼 취하고 역순으로 바꾸기
        df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
        # print(df_read_use)
        # print(len(df_read_use))
        if stock_price_candle_cnt > len(df_read_use):
            continue

        y_s = df_read_use['stock_start']
        y_h = df_read_use['stock_high']
        y_l = df_read_use['stock_low']
        y_c = df_read_use['stock_end']
        # print(y_h)

        x_index = []
        for i in range(stock_price_candle_cnt):
            x_index.append(i)
        # print(x_index)
        x_index_np = np.array(x_index)
        # print(x_index_np)
        # x_index_np 2차원 array 형태로 변경
        x_train = x_index_np.reshape(-1, 1)
        # print(x_train)

        stock_start = df_read_use['stock_start'].values
        stock_high = df_read_use['stock_high'].values
        stock_low = df_read_use['stock_low'].values
        stock_close = df_read_use['stock_end'].values
        # print(stock_high)
        y_start = stock_start.reshape(-1, 1)
        y_high = stock_high.reshape(-1, 1)
        y_low = stock_low.reshape(-1, 1)
        y_close = stock_close.reshape(-1, 1)
        # print(y_high)
        # print('x_train.shape : ', x_train.shape)
        # print('y_high.shape : ', y_high.shape)

        # =====
        # 모델 생성
        # $\hat y = 0.5x^2+x+2+Gaussian\, noise$ 의 모델을 만든다.
        # np.random.rand(100,1)
        # 0~1 사이의 값을 [100,1]로 난수 생성
        # np.random.randn(100,1)
        # 평균 0, 표준편차 1인 값을 [100,1]로 난수 생성
        # PolynomialFeatures(degree = n, include_bias = True | False, interaction_only = True | False)
        # n항 차수 변환 및 교호작용 변수 생성
        # include_bias = True를 옵션으로 주면 편향 특성$x_0 = 1$이 추가
        # interaction_only = True를 옵션으로 주면 교호작용 변수만 생성
        # x_train_poly = poly_features.fit_transform(X)
        # 데이터 X를 n차항이 적용된 다항 회귀 모델로 변형

        # m = 100
        # X = 6 * np.random.rand(m, 1) - 3
        # y = 0.5 * X**2 + X + 2 + np.random.randn(100, 1)
        # print(X)    # 2차원 배열
        # print(y)    # 2차원 배열
        # [[ 0.60854935]
        #  [ 2.19477949]
        #  [ 0.09632116]
        #  [-2.81841897]
        # ....
        #  [ 2.31860528]
        #  [ 4.37030102]
        #  [ 9.35967444]
        #  [ 2.57697657]]

        # =====
        # 모델생성
        # 사이킷런을 이용한 다항회귀모델 추정
        # 사이킷런의 LinearRegression 함수등을 사용하여 다항 회귀 모델 추정
        # LinearRegression()
        # 사이킷런에서 제공하는 LinearRegression 클래스
        # Attribute
        # intercept_ : 상수항 출력
        # coef_ : 계수 출력
        # 함수
        # fix(X,y) : Fit linear model
        # get_params(self, deep=True) : Get parameters for this estimator.
        # predict(self, X) : Predict using the linear model
        # score(self, X, y, sample_weight=None) : Returns the coefficient of determination R^2 of the prediction.
        # set_params(self, **params) : Set the parameters of this estimator.

        # 사이킷런 사용
        poly_features = PolynomialFeatures(degree=3, include_bias=False)
        x_train_poly = poly_features.fit_transform(x_train)
        # 모델생성
        poly_model_s = LinearRegression()
        poly_model_h = LinearRegression()
        poly_model_l = LinearRegression()
        poly_model_c = LinearRegression()
        # 모델훈련
        poly_model_s.fit(x_train_poly, y_start)
        poly_model_h.fit(x_train_poly, y_high)
        poly_model_l.fit(x_train_poly, y_low)
        poly_model_c.fit(x_train_poly, y_close)

        # 사이킷런 사용
        X_new_poly = poly_features.transform(x_train)
        poly_pred_s = poly_model_s.predict(X_new_poly)
        poly_pred_h = poly_model_h.predict(X_new_poly)
        poly_pred_l = poly_model_l.predict(X_new_poly)
        poly_pred_c = poly_model_c.predict(X_new_poly)

        stock_price_day_cnt_2cha = [[stock_price_candle_cnt]]
        new_stock_price_day_cnt_2cha = poly_features.transform(stock_price_day_cnt_2cha)
        poly_pred_twenty_h = poly_model_h.predict(new_stock_price_day_cnt_2cha)
        poly_pred_twenty_l = poly_model_l.predict(new_stock_price_day_cnt_2cha)
        # print(poly_pred_h)
        # print(poly_pred_twenty_h)
        # print(poly_pred_l)
        # print(poly_pred_twenty_l)

        # poly_model_c.intercept_, poly_model_c.coef_
        # 절편
        # print(poly_model_h.intercept_)
        # print(poly_model_l.intercept_)
        # 기울기
        poly_h_gradient = poly_model_h.coef_
        poly_l_gradient = poly_model_l.coef_
        # print(poly_h_gradient)
        # print(poly_l_gradient)

        # 모델생성
        line_model_s = LinearRegression()
        line_model_h = LinearRegression()
        line_model_l = LinearRegression()
        line_model_c = LinearRegression()
        # 모델훈련
        line_model_s.fit(x_train, y_s)
        line_model_h.fit(x_train, y_h)
        line_model_l.fit(x_train, y_l)
        line_model_c.fit(x_train, y_c)
        # 예상하기
        line_pred_s = line_model_s.predict(x_train)
        line_pred_h = line_model_h.predict(x_train)
        line_pred_l = line_model_l.predict(x_train)
        line_pred_c = line_model_c.predict(x_train)

        line_pred_twenty_h = line_model_h.predict([[stock_price_candle_cnt]])
        line_pred_twenty_l = line_model_l.predict([[stock_price_candle_cnt]])
        # print(line_pred_h)
        # print(line_pred_twenty_h)
        # print(line_pred_l)
        # print(line_pred_twenty_l)

        # 추세선 기준 고가/저가 구하고 최대값 최소값 구하기
        poly_pred_high_diff_price = []
        poly_pred_low_diff_price = []
        pred_high_diff_price = []
        pred_low_diff_price = []
        for i in range(stock_price_candle_cnt):
            # poly
            poly_pred_high_diff_price.append(stock_high[i] - poly_pred_h[i][-1])
            # print(stock_high[i])
            # print(poly_pred_h[i])
            poly_pred_low_diff_price.append(poly_pred_l[i][-1] - stock_low[i])
            poly_pred_nineteen_h = poly_pred_h[i][-1]
            poly_pred_nineteen_l = poly_pred_l[i][-1]

            # 위에서 인덱스를 뒤집었으므로 꺼꾸로 계산
            pred_high_diff_price.append(y_h[(stock_price_candle_cnt - 1) - i] - line_pred_h[i])
            # print(y_h[(stock_price_candle_cnt - 1) - i])
            # print(line_pred_h[i])
            pred_low_diff_price.append(line_pred_l[i] - y_l[(stock_price_candle_cnt - 1) - i])
            line_pred_nineteen_h = line_pred_h[i]
            line_pred_nineteen_l = line_pred_l[i]
        # print(poly_pred_high_diff_price)
        # print(poly_pred_low_diff_price)
        poly_pred_high_diff_price_max = max(poly_pred_high_diff_price)
        poly_pred_low_diff_price_max = max(poly_pred_low_diff_price)
        pred_high_diff_price_max = max(pred_high_diff_price)
        pred_low_diff_price_max = max(pred_low_diff_price)
        # 추세선 기준으로 고가 혹은 저가와의 차이 최대값
        # print(poly_pred_high_diff_price_max)
        # print(poly_pred_low_diff_price_max)
        # print(pred_high_diff_price_max)
        # print(pred_low_diff_price_max)
        # 매도최대값 / 매수최저값
        # print(poly_pred_nineteen_h)
        # print(poly_pred_nineteen_l)
        # print(line_pred_nineteen_h)
        # print(line_pred_nineteen_l)
        poly_sell_max_price = poly_pred_nineteen_h + poly_pred_high_diff_price_max
        poly_buy_min_price = poly_pred_nineteen_l - poly_pred_low_diff_price_max
        sell_max_price = line_pred_nineteen_h + pred_high_diff_price_max
        buy_min_price = line_pred_nineteen_l - pred_low_diff_price_max
        # print(poly_sell_max_price)
        # print(poly_buy_min_price)
        # print(sell_max_price)
        # print(buy_min_price)
        # 기울기
        line_h_gradient = line_model_h.coef_
        line_l_gradient = line_model_l.coef_
        # print(line_h_gradient)
        # print(line_l_gradient)

        # 테이타 생성
        stock_trend_line_of_ai['stock_no'].append(table_name)
        stock_trend_line_of_ai['poly_sell_max_price'].append(poly_sell_max_price)
        stock_trend_line_of_ai['poly_buy_min_price'].append(poly_buy_min_price)
        stock_trend_line_of_ai['sell_max_price'].append(sell_max_price)
        stock_trend_line_of_ai['buy_min_price'].append(buy_min_price)
        stock_trend_line_of_ai['poly_h_gradient'].append(poly_h_gradient[-1][-1])
        stock_trend_line_of_ai['poly_l_gradient'].append(poly_l_gradient[-1][-1])
        stock_trend_line_of_ai['h_gradient'].append(line_h_gradient[-1])
        stock_trend_line_of_ai['l_gradient'].append(line_l_gradient[-1])
        # 추가저장(20240201)
        stock_trend_line_of_ai['candle_cnt'].append(stock_price_candle_cnt)
        stock_trend_line_of_ai['text_time'].append(text_time)
        # print(stock_trend_line_of_ai)

        # # =====
        # # 선형 회귀 모델 표현¶
        # # python의 plot을 이용하여 출력
        # plt.plot(x_index, stock_start, 'c.')
        # plt.plot(x_index, stock_high, 'ro')
        # plt.plot(x_index, stock_low, 'bo')
        # plt.plot(x_index, stock_close, 'm.')
        # plt.plot(x_index, poly_pred_h, 'r-')
        # plt.plot(x_index, poly_pred_l, 'b-')
        # plt.plot(x_index, line_pred_h, 'm-')
        # plt.plot(x_index, line_pred_l, 'c-')
        # plt.title(table_name)
        #
        # # Show the major grid lines with dark grey lines
        # plt.grid(b=True, which='major', color='#999999', linestyle='-')
        # # Show the minor grid lines with very faint and almost transparent grey lines
        # plt.minorticks_on()
        # plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        #
        # plt.tight_layout()
        # plt.show()
    # db닫기
    con.commit()
    con.close()

    # print(stock_trend_line_of_ai)

    # 저장
    df = pd.DataFrame(stock_trend_line_of_ai,
                      columns=['poly_sell_max_price', 'poly_buy_min_price',
                               'sell_max_price', 'buy_min_price',
                               'poly_h_gradient', 'poly_l_gradient', 'h_gradient', 'l_gradient',
                               'candle_cnt', 'text_time'],
                      index=stock_trend_line_of_ai['stock_no'])

    con = sqlite3.connect(db_file_path + '/' + put_db_name)
    df.to_sql(current_today, con, if_exists='append', index_label='stock_no')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # index_label	인덱스 칼럼에 대한 라벨을 지정
    # db닫기
    con.commit()
    con.close()

def future_s_simul_of_trend_line_day_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt):
    # 1. 데이터셋 생성하기
    # db 저장폴더

    # 테이블명 가져오기
    con = sqlite3.connect(db_file_path + '/' + get_db_name)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    total_table_name_of_db = cursor.fetchall()
    # print(total_table_name_of_db)
    # 실제 테이블 구하기
    total_table_name = []
    for table in total_table_name_of_db:
        total_table_name.append(table[0])
    # print(total_table_name)

    # total_table_name = ['000660']
    # 실행파일에서 인자 받아서 처리하기
    if len(sys.argv) > 1:
        print(sys.argv[0])  # 파일명
        print(sys.argv[1])  # 첫번째 인자
        total_table_name = [sys.argv[1]]
    # print(total_table_name)

    for table_name in total_table_name:
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()

        # 지난 일봉 시뮬레이션
        day_market_sell_buy_time = {'running_stock_date': [], 'running_y_h': [], 'running_y_l': [], 'sell_mode': [], 'buy_mode': [],
                                      'poly_h_gradient': [], 'poly_l_gradient': [], 'poly_sell_max_price': [], 'poly_buy_min_price': []}
        for m in range(len(df_read) - stock_price_candle_cnt):
            # 가장 최근월의 고가/저가 구하기
            running_stock_date = df_read.iloc[m]['stock_date']
            running_y_h = df_read.iloc[m]['stock_high']
            running_y_l = df_read.iloc[m]['stock_low']
            # print(running_y_h)
            # print(running_y_l)

            # pd 필요건수 만큼 취하고 / 역순으로 바꾸기
            # df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
            df_read_cntget = df_read.iloc[m + 1:stock_price_candle_cnt + m + 1]     # 당월은 고가/저가만 취하고 지난일까지 20개 데이타로 비교(+1 더함)
            df_read_use = df_read_cntget[::-1]
            # print(df_read_use)
            # print(len(df_read_use))
            # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
            min_index = df_read_use.index.min()

            if stock_price_candle_cnt > len(df_read_use):
                print('혹시 데이타 오바인가?')
                continue

            y_s = df_read_use['stock_start']
            y_h = df_read_use['stock_high']
            y_l = df_read_use['stock_low']
            y_c = df_read_use['stock_end']
            # print(y_h)

            x_index = []
            for i in range(stock_price_candle_cnt):
                x_index.append(i)
            # print(x_index)
            x_index_np = np.array(x_index)
            # print(x_index_np)
            # x_index_np 2차원 array 형태로 변경
            x_train = x_index_np.reshape(-1, 1)
            # print(x_train)

            stock_start = df_read_use['stock_start'].values
            stock_high = df_read_use['stock_high'].values
            stock_low = df_read_use['stock_low'].values
            stock_close = df_read_use['stock_end'].values
            # print(stock_high)
            y_start = stock_start.reshape(-1, 1)
            y_high = stock_high.reshape(-1, 1)
            y_low = stock_low.reshape(-1, 1)
            y_close = stock_close.reshape(-1, 1)
            # print(y_high)
            # print('x_train.shape : ', x_train.shape)
            # print('y_high.shape : ', y_high.shape)

            # =====
            # 모델 생성
            # $\hat y = 0.5x^2+x+2+Gaussian\, noise$ 의 모델을 만든다.
            # np.random.rand(100,1)
            # 0~1 사이의 값을 [100,1]로 난수 생성
            # np.random.randn(100,1)
            # 평균 0, 표준편차 1인 값을 [100,1]로 난수 생성
            # PolynomialFeatures(degree = n, include_bias = True | False, interaction_only = True | False)
            # n항 차수 변환 및 교호작용 변수 생성
            # include_bias = True를 옵션으로 주면 편향 특성$x_0 = 1$이 추가
            # interaction_only = True를 옵션으로 주면 교호작용 변수만 생성
            # x_train_poly = poly_features.fit_transform(X)
            # 데이터 X를 n차항이 적용된 다항 회귀 모델로 변형

            # m = 100
            # X = 6 * np.random.rand(m, 1) - 3
            # y = 0.5 * X**2 + X + 2 + np.random.randn(100, 1)
            # print(X)    # 2차원 배열
            # print(y)    # 2차원 배열
            # [[ 0.60854935]
            #  [ 2.19477949]
            #  [ 0.09632116]
            #  [-2.81841897]
            # ....
            #  [ 2.31860528]
            #  [ 4.37030102]
            #  [ 9.35967444]
            #  [ 2.57697657]]

            # =====
            # 모델생성
            # 사이킷런을 이용한 다항회귀모델 추정
            # 사이킷런의 LinearRegression 함수등을 사용하여 다항 회귀 모델 추정
            # LinearRegression()
            # 사이킷런에서 제공하는 LinearRegression 클래스
            # Attribute
            # intercept_ : 상수항 출력
            # coef_ : 계수 출력
            # 함수
            # fix(X,y) : Fit linear model
            # get_params(self, deep=True) : Get parameters for this estimator.
            # predict(self, X) : Predict using the linear model
            # score(self, X, y, sample_weight=None) : Returns the coefficient of determination R^2 of the prediction.
            # set_params(self, **params) : Set the parameters of this estimator.

            # 사이킷런 사용
            poly_features = PolynomialFeatures(degree=3, include_bias=False)
            x_train_poly = poly_features.fit_transform(x_train)
            # 모델생성
            poly_model_s = LinearRegression()
            poly_model_h = LinearRegression()
            poly_model_l = LinearRegression()
            poly_model_c = LinearRegression()
            # 모델훈련
            poly_model_s.fit(x_train_poly, y_start)
            poly_model_h.fit(x_train_poly, y_high)
            poly_model_l.fit(x_train_poly, y_low)
            poly_model_c.fit(x_train_poly, y_close)

            # 사이킷런 사용
            X_new_poly = poly_features.transform(x_train)
            poly_pred_s = poly_model_s.predict(X_new_poly)
            poly_pred_h = poly_model_h.predict(X_new_poly)
            poly_pred_l = poly_model_l.predict(X_new_poly)
            poly_pred_c = poly_model_c.predict(X_new_poly)

            stock_price_day_cnt_2cha = [[stock_price_candle_cnt]]
            new_stock_price_day_cnt_2cha = poly_features.transform(stock_price_day_cnt_2cha)
            poly_pred_twenty_h = poly_model_h.predict(new_stock_price_day_cnt_2cha)
            poly_pred_twenty_l = poly_model_l.predict(new_stock_price_day_cnt_2cha)
            # print(poly_pred_h)
            # print(poly_pred_twenty_h)
            # print(poly_pred_l)
            # print(poly_pred_twenty_l)

            # poly_model_c.intercept_, poly_model_c.coef_
            # 절편
            # print(poly_model_h.intercept_)
            # print(poly_model_l.intercept_)
            # 기울기
            poly_h_gradient = poly_model_h.coef_
            poly_l_gradient = poly_model_l.coef_
            # print(poly_h_gradient)
            # print(poly_l_gradient)

            # 모델생성
            line_model_s = LinearRegression()
            line_model_h = LinearRegression()
            line_model_l = LinearRegression()
            line_model_c = LinearRegression()
            # 모델훈련
            line_model_s.fit(x_train, y_s)
            line_model_h.fit(x_train, y_h)
            line_model_l.fit(x_train, y_l)
            line_model_c.fit(x_train, y_c)
            # 예상하기
            line_pred_s = line_model_s.predict(x_train)
            line_pred_h = line_model_h.predict(x_train)
            line_pred_l = line_model_l.predict(x_train)
            line_pred_c = line_model_c.predict(x_train)

            line_pred_twenty_h = line_model_h.predict([[stock_price_candle_cnt]])
            line_pred_twenty_l = line_model_l.predict([[stock_price_candle_cnt]])
            # print(line_pred_h)
            # print(line_pred_twenty_h)
            # print(line_pred_l)
            # print(line_pred_twenty_l)

            # 추세선 기준 고가/저가 구하고 최대값 최소값 구하기
            poly_pred_high_diff_price = []
            poly_pred_low_diff_price = []
            pred_high_diff_price = []
            pred_low_diff_price = []
            for i in range(stock_price_candle_cnt):
                # poly
                poly_pred_high_diff_price.append(stock_high[i] - poly_pred_h[i][-1])
                # print(stock_high[i])
                # print(poly_pred_h[i])
                poly_pred_low_diff_price.append(poly_pred_l[i][-1] - stock_low[i])
                poly_pred_nineteen_h = poly_pred_h[i][-1]
                poly_pred_nineteen_l = poly_pred_l[i][-1]

                # 위에서 인덱스를 뒤집었으므로 꺼꾸로 계산
                pred_high_diff_price.append(y_h[(stock_price_candle_cnt - 1 + min_index) - i] - line_pred_h[i])
                # print(y_h[(stock_price_candle_cnt - 1 + min_index) - i])
                # print(line_pred_h[i])
                pred_low_diff_price.append(line_pred_l[i] - y_l[(stock_price_candle_cnt - 1 + min_index) - i])
                line_pred_nineteen_h = line_pred_h[i]
                line_pred_nineteen_l = line_pred_l[i]
            # print(poly_pred_high_diff_price)
            # print(poly_pred_low_diff_price)
            poly_pred_high_diff_price_max = max(poly_pred_high_diff_price)
            poly_pred_low_diff_price_max = max(poly_pred_low_diff_price)
            pred_high_diff_price_max = max(pred_high_diff_price)
            pred_low_diff_price_max = max(pred_low_diff_price)
            # 추세선 기준으로 고가 혹은 저가와의 차이 최대값
            # print(poly_pred_high_diff_price_max)
            # print(poly_pred_low_diff_price_max)
            # print(pred_high_diff_price_max)
            # print(pred_low_diff_price_max)
            # 매도최대값 / 매수최저값
            # print(poly_pred_nineteen_h)
            # print(poly_pred_nineteen_l)
            # print(line_pred_nineteen_h)
            # print(line_pred_nineteen_l)
            poly_sell_max_price = poly_pred_nineteen_h + poly_pred_high_diff_price_max
            poly_buy_min_price = poly_pred_nineteen_l - poly_pred_low_diff_price_max
            sell_max_price = line_pred_nineteen_h + pred_high_diff_price_max
            buy_min_price = line_pred_nineteen_l - pred_low_diff_price_max
            # print(poly_sell_max_price)
            # print(poly_buy_min_price)
            poly_sell_max_price_for_graph = []
            poly_buy_min_price_for_graph = []
            for i in range(stock_price_candle_cnt):
                # max/min 그래프 그리는 용
                poly_sell_max_price_for_graph.append(poly_sell_max_price)
                poly_buy_min_price_for_graph.append(poly_buy_min_price)
            # print(sell_max_price)
            # print(buy_min_price)
            # 기울기
            line_h_gradient = line_model_h.coef_
            line_l_gradient = line_model_l.coef_
            # print(line_h_gradient)
            # print(line_l_gradient)

            # 값구하기(일봉 max/min 비교)
            if (running_y_h > poly_sell_max_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(1)
                day_market_sell_buy_time['buy_mode'].append(0)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
            elif (running_y_l < poly_buy_min_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(0)
                day_market_sell_buy_time['buy_mode'].append(1)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
        # print(day_market_sell_buy_time)

    # db닫기
    con.commit()
    con.close()

    # 저장
    df = pd.DataFrame(day_market_sell_buy_time,
                      columns=['running_y_h', 'running_y_l', 'sell_mode', 'buy_mode',
                               'poly_h_gradient', 'poly_l_gradient', 'poly_sell_max_price', 'poly_buy_min_price'],
                      index=day_market_sell_buy_time['running_stock_date'])

    con = sqlite3.connect(db_file_path + '/' + put_db_name)
    df.to_sql(current_today, con, if_exists='replace', index_label='deal_day')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
    # index_label	인덱스 칼럼에 대한 라벨을 지정

def future_s_simul_of_trend_line_store_2060(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt):
    # 1. 데이터셋 생성하기
    # db 저장폴더

    # 테이블명 가져오기
    con = sqlite3.connect(db_file_path + '/' + get_db_name)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    total_table_name_of_db = cursor.fetchall()
    # print(total_table_name_of_db)
    # 실제 테이블 구하기
    total_table_name = []
    for table in total_table_name_of_db:
        total_table_name.append(table[0])
    # print(total_table_name)

    # total_table_name = ['000660']
    # 실행파일에서 인자 받아서 처리하기
    if len(sys.argv) > 1:
        print(sys.argv[0])  # 파일명
        print(sys.argv[1])  # 첫번째 인자
        total_table_name = [sys.argv[1]]
    # print(total_table_name)

    for table_name in total_table_name:
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()

        # 지난 일봉 시뮬레이션
        day_market_sell_buy_time = {'running_stock_date': [], 'running_y_h': [], 'running_y_l': [], 'sell_mode': [], 'buy_mode': [],
                                      'poly_h_gradient': [], 'poly_l_gradient': [], 'poly_sell_max_price': [], 'poly_buy_min_price': []}
        for m in range(len(df_read) - stock_price_candle_cnt):
            # 가장 최근월의 고가/저가 구하기
            running_stock_date = df_read.iloc[m]['stock_date']
            running_y_h = df_read.iloc[m]['stock_high']
            running_y_l = df_read.iloc[m]['stock_low']
            # print(running_y_h)
            # print(running_y_l)

            # pd 필요건수 만큼 취하고 / 역순으로 바꾸기
            # df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
            # df_read_cntget = df_read.iloc[m + 1:stock_price_candle_cnt + m + 1]     # 당월은 고가/저가만 취하고 지난일까지 20개 데이타로 비교(+1 더함)
            df_read_cntget = df_read.iloc[m:stock_price_candle_cnt + m]  # 당월은 고가/저가만 취하고 지난일까지 20개 데이타로 비교(+1 더함)
            df_read_use = df_read_cntget[::-1]
            # print(df_read_use)
            # print(len(df_read_use))
            # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
            min_index = df_read_use.index.min()

            if stock_price_candle_cnt > len(df_read_use):
                print('혹시 데이타 오바인가?')
                continue

            y_s = df_read_use['stock_start']
            y_h = df_read_use['stock_high']
            y_l = df_read_use['stock_low']
            y_c = df_read_use['stock_end']
            # print(y_h)

            x_index = []
            for i in range(stock_price_candle_cnt):
                x_index.append(i)
            # print(x_index)
            x_index_np = np.array(x_index)
            # print(x_index_np)
            # x_index_np 2차원 array 형태로 변경
            x_train = x_index_np.reshape(-1, 1)
            # print(x_train)

            stock_start = df_read_use['stock_start'].values
            stock_high = df_read_use['stock_high'].values
            stock_low = df_read_use['stock_low'].values
            stock_close = df_read_use['stock_end'].values
            # print(stock_high)
            y_start = stock_start.reshape(-1, 1)
            y_high = stock_high.reshape(-1, 1)
            y_low = stock_low.reshape(-1, 1)
            y_close = stock_close.reshape(-1, 1)
            # print(y_high)
            # print('x_train.shape : ', x_train.shape)
            # print('y_high.shape : ', y_high.shape)

            # =====
            # 모델 생성
            # $\hat y = 0.5x^2+x+2+Gaussian\, noise$ 의 모델을 만든다.
            # np.random.rand(100,1)
            # 0~1 사이의 값을 [100,1]로 난수 생성
            # np.random.randn(100,1)
            # 평균 0, 표준편차 1인 값을 [100,1]로 난수 생성
            # PolynomialFeatures(degree = n, include_bias = True | False, interaction_only = True | False)
            # n항 차수 변환 및 교호작용 변수 생성
            # include_bias = True를 옵션으로 주면 편향 특성$x_0 = 1$이 추가
            # interaction_only = True를 옵션으로 주면 교호작용 변수만 생성
            # x_train_poly = poly_features.fit_transform(X)
            # 데이터 X를 n차항이 적용된 다항 회귀 모델로 변형

            # m = 100
            # X = 6 * np.random.rand(m, 1) - 3
            # y = 0.5 * X**2 + X + 2 + np.random.randn(100, 1)
            # print(X)    # 2차원 배열
            # print(y)    # 2차원 배열
            # [[ 0.60854935]
            #  [ 2.19477949]
            #  [ 0.09632116]
            #  [-2.81841897]
            # ....
            #  [ 2.31860528]
            #  [ 4.37030102]
            #  [ 9.35967444]
            #  [ 2.57697657]]

            # =====
            # 모델생성
            # 사이킷런을 이용한 다항회귀모델 추정
            # 사이킷런의 LinearRegression 함수등을 사용하여 다항 회귀 모델 추정
            # LinearRegression()
            # 사이킷런에서 제공하는 LinearRegression 클래스
            # Attribute
            # intercept_ : 상수항 출력
            # coef_ : 계수 출력
            # 함수
            # fix(X,y) : Fit linear model
            # get_params(self, deep=True) : Get parameters for this estimator.
            # predict(self, X) : Predict using the linear model
            # score(self, X, y, sample_weight=None) : Returns the coefficient of determination R^2 of the prediction.
            # set_params(self, **params) : Set the parameters of this estimator.

            # 사이킷런 사용
            poly_features = PolynomialFeatures(degree=3, include_bias=False)
            x_train_poly = poly_features.fit_transform(x_train)
            # 모델생성
            poly_model_s = LinearRegression()
            poly_model_h = LinearRegression()
            poly_model_l = LinearRegression()
            poly_model_c = LinearRegression()
            # 모델훈련
            poly_model_s.fit(x_train_poly, y_start)
            poly_model_h.fit(x_train_poly, y_high)
            poly_model_l.fit(x_train_poly, y_low)
            poly_model_c.fit(x_train_poly, y_close)

            # 사이킷런 사용
            X_new_poly = poly_features.transform(x_train)
            poly_pred_s = poly_model_s.predict(X_new_poly)
            poly_pred_h = poly_model_h.predict(X_new_poly)
            poly_pred_l = poly_model_l.predict(X_new_poly)
            poly_pred_c = poly_model_c.predict(X_new_poly)

            stock_price_day_cnt_2cha = [[stock_price_candle_cnt]]
            new_stock_price_day_cnt_2cha = poly_features.transform(stock_price_day_cnt_2cha)
            poly_pred_twenty_h = poly_model_h.predict(new_stock_price_day_cnt_2cha)
            poly_pred_twenty_l = poly_model_l.predict(new_stock_price_day_cnt_2cha)
            # print(poly_pred_h)
            # print(poly_pred_twenty_h)
            # print(poly_pred_l)
            # print(poly_pred_twenty_l)

            # poly_model_c.intercept_, poly_model_c.coef_
            # 절편
            # print(poly_model_h.intercept_)
            # print(poly_model_l.intercept_)
            # 기울기
            poly_h_gradient = poly_model_h.coef_
            poly_l_gradient = poly_model_l.coef_
            # print(poly_h_gradient)
            # print(poly_l_gradient)

            # 모델생성
            line_model_s = LinearRegression()
            line_model_h = LinearRegression()
            line_model_l = LinearRegression()
            line_model_c = LinearRegression()
            # 모델훈련
            line_model_s.fit(x_train, y_s)
            line_model_h.fit(x_train, y_h)
            line_model_l.fit(x_train, y_l)
            line_model_c.fit(x_train, y_c)
            # 예상하기
            line_pred_s = line_model_s.predict(x_train)
            line_pred_h = line_model_h.predict(x_train)
            line_pred_l = line_model_l.predict(x_train)
            line_pred_c = line_model_c.predict(x_train)

            line_pred_twenty_h = line_model_h.predict([[stock_price_candle_cnt]])
            line_pred_twenty_l = line_model_l.predict([[stock_price_candle_cnt]])
            # print(line_pred_h)
            # print(line_pred_twenty_h)
            # print(line_pred_l)
            # print(line_pred_twenty_l)

            # 추세선 기준 고가/저가 구하고 최대값 최소값 구하기
            poly_pred_high_diff_price = []
            poly_pred_low_diff_price = []
            pred_high_diff_price = []
            pred_low_diff_price = []
            for i in range(stock_price_candle_cnt):
                # poly
                poly_pred_high_diff_price.append(stock_high[i] - poly_pred_h[i][-1])
                # print(stock_high[i])
                # print(poly_pred_h[i])
                poly_pred_low_diff_price.append(poly_pred_l[i][-1] - stock_low[i])
                poly_pred_nineteen_h = poly_pred_h[i][-1]
                poly_pred_nineteen_l = poly_pred_l[i][-1]

                # 위에서 인덱스를 뒤집었으므로 꺼꾸로 계산
                pred_high_diff_price.append(y_h[(stock_price_candle_cnt - 1 + min_index) - i] - line_pred_h[i])
                # print(y_h[(stock_price_candle_cnt - 1 + min_index) - i])
                # print(line_pred_h[i])
                pred_low_diff_price.append(line_pred_l[i] - y_l[(stock_price_candle_cnt - 1 + min_index) - i])
                line_pred_nineteen_h = line_pred_h[i]
                line_pred_nineteen_l = line_pred_l[i]
            # print(poly_pred_high_diff_price)
            # print(poly_pred_low_diff_price)
            poly_pred_high_diff_price_max = max(poly_pred_high_diff_price)
            poly_pred_low_diff_price_max = max(poly_pred_low_diff_price)
            pred_high_diff_price_max = max(pred_high_diff_price)
            pred_low_diff_price_max = max(pred_low_diff_price)
            # 추세선 기준으로 고가 혹은 저가와의 차이 최대값
            # print(poly_pred_high_diff_price_max)
            # print(poly_pred_low_diff_price_max)
            # print(pred_high_diff_price_max)
            # print(pred_low_diff_price_max)
            # 매도최대값 / 매수최저값
            # print(poly_pred_nineteen_h)
            # print(poly_pred_nineteen_l)
            # print(line_pred_nineteen_h)
            # print(line_pred_nineteen_l)
            poly_sell_max_price = poly_pred_nineteen_h + poly_pred_high_diff_price_max
            poly_buy_min_price = poly_pred_nineteen_l - poly_pred_low_diff_price_max
            sell_max_price = line_pred_nineteen_h + pred_high_diff_price_max
            buy_min_price = line_pred_nineteen_l - pred_low_diff_price_max
            # print(poly_sell_max_price)
            # print(poly_buy_min_price)
            poly_sell_max_price_for_graph = []
            poly_buy_min_price_for_graph = []
            for i in range(stock_price_candle_cnt):
                # max/min 그래프 그리는 용
                poly_sell_max_price_for_graph.append(poly_sell_max_price)
                poly_buy_min_price_for_graph.append(poly_buy_min_price)
            # print(sell_max_price)
            # print(buy_min_price)
            # 기울기
            line_h_gradient = line_model_h.coef_
            line_l_gradient = line_model_l.coef_
            # print(line_h_gradient)
            # print(line_l_gradient)

            # 값구하기(일봉 max/min 비교)
            if (running_y_h >= poly_sell_max_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(1)
                day_market_sell_buy_time['buy_mode'].append(0)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
            elif (running_y_l <= poly_buy_min_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(0)
                day_market_sell_buy_time['buy_mode'].append(1)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
        # print(day_market_sell_buy_time)

    # db닫기
    con.commit()
    con.close()

    # 저장
    df = pd.DataFrame(day_market_sell_buy_time,
                      columns=['running_y_h', 'running_y_l', 'sell_mode', 'buy_mode',
                               'poly_h_gradient', 'poly_l_gradient', 'poly_sell_max_price', 'poly_buy_min_price'],
                      index=day_market_sell_buy_time['running_stock_date'])

    con = sqlite3.connect(db_file_path + '/' + put_db_name)
    df.to_sql(current_today, con, if_exists='replace', index_label='deal_day')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
    # index_label	인덱스 칼럼에 대한 라벨을 지정

def future_s_simul_of_trend_line_store_2161(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt):
    # 1. 데이터셋 생성하기
    # db 저장폴더

    # 테이블명 가져오기
    con = sqlite3.connect(db_file_path + '/' + get_db_name)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    total_table_name_of_db = cursor.fetchall()
    # print(total_table_name_of_db)
    # 실제 테이블 구하기
    total_table_name = []
    for table in total_table_name_of_db:
        total_table_name.append(table[0])
    # print(total_table_name)

    # total_table_name = ['000660']
    # 실행파일에서 인자 받아서 처리하기
    if len(sys.argv) > 1:
        print(sys.argv[0])  # 파일명
        print(sys.argv[1])  # 첫번째 인자
        total_table_name = [sys.argv[1]]
    # print(total_table_name)

    for table_name in total_table_name:
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()

        # 지난 일봉 시뮬레이션
        day_market_sell_buy_time = {'running_stock_date': [], 'running_y_h': [], 'running_y_l': [], 'sell_mode': [], 'buy_mode': [],
                                      'poly_h_gradient': [], 'poly_l_gradient': [], 'poly_sell_max_price': [], 'poly_buy_min_price': []}
        for m in range(len(df_read) - stock_price_candle_cnt):
            # 가장 최근월의 고가/저가 구하기
            running_stock_date = df_read.iloc[m]['stock_date']
            running_y_h = df_read.iloc[m]['stock_high']
            running_y_l = df_read.iloc[m]['stock_low']
            # print(running_y_h)
            # print(running_y_l)

            # pd 필요건수 만큼 취하고 / 역순으로 바꾸기
            # df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
            df_read_cntget = df_read.iloc[m + 1:stock_price_candle_cnt + m + 1]     # 당월은 고가/저가만 취하고 지난일까지 20개 데이타로 비교(+1 더함)
            # df_read_cntget = df_read.iloc[m:stock_price_candle_cnt + m]  # 당월은 고가/저가만 취하고 지난일까지 20개 데이타로 비교(+1 더함)
            df_read_use = df_read_cntget[::-1]
            # print(df_read_use)
            # print(len(df_read_use))
            # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
            min_index = df_read_use.index.min()

            if stock_price_candle_cnt > len(df_read_use):
                print('혹시 데이타 오바인가?')
                continue

            y_s = df_read_use['stock_start']
            y_h = df_read_use['stock_high']
            y_l = df_read_use['stock_low']
            y_c = df_read_use['stock_end']
            # print(y_h)

            x_index = []
            for i in range(stock_price_candle_cnt):
                x_index.append(i)
            # print(x_index)
            x_index_np = np.array(x_index)
            # print(x_index_np)
            # x_index_np 2차원 array 형태로 변경
            x_train = x_index_np.reshape(-1, 1)
            # print(x_train)

            stock_start = df_read_use['stock_start'].values
            stock_high = df_read_use['stock_high'].values
            stock_low = df_read_use['stock_low'].values
            stock_close = df_read_use['stock_end'].values
            # print(stock_high)
            y_start = stock_start.reshape(-1, 1)
            y_high = stock_high.reshape(-1, 1)
            y_low = stock_low.reshape(-1, 1)
            y_close = stock_close.reshape(-1, 1)
            # print(y_high)
            # print('x_train.shape : ', x_train.shape)
            # print('y_high.shape : ', y_high.shape)

            # =====
            # 모델 생성
            # $\hat y = 0.5x^2+x+2+Gaussian\, noise$ 의 모델을 만든다.
            # np.random.rand(100,1)
            # 0~1 사이의 값을 [100,1]로 난수 생성
            # np.random.randn(100,1)
            # 평균 0, 표준편차 1인 값을 [100,1]로 난수 생성
            # PolynomialFeatures(degree = n, include_bias = True | False, interaction_only = True | False)
            # n항 차수 변환 및 교호작용 변수 생성
            # include_bias = True를 옵션으로 주면 편향 특성$x_0 = 1$이 추가
            # interaction_only = True를 옵션으로 주면 교호작용 변수만 생성
            # x_train_poly = poly_features.fit_transform(X)
            # 데이터 X를 n차항이 적용된 다항 회귀 모델로 변형

            # m = 100
            # X = 6 * np.random.rand(m, 1) - 3
            # y = 0.5 * X**2 + X + 2 + np.random.randn(100, 1)
            # print(X)    # 2차원 배열
            # print(y)    # 2차원 배열
            # [[ 0.60854935]
            #  [ 2.19477949]
            #  [ 0.09632116]
            #  [-2.81841897]
            # ....
            #  [ 2.31860528]
            #  [ 4.37030102]
            #  [ 9.35967444]
            #  [ 2.57697657]]

            # =====
            # 모델생성
            # 사이킷런을 이용한 다항회귀모델 추정
            # 사이킷런의 LinearRegression 함수등을 사용하여 다항 회귀 모델 추정
            # LinearRegression()
            # 사이킷런에서 제공하는 LinearRegression 클래스
            # Attribute
            # intercept_ : 상수항 출력
            # coef_ : 계수 출력
            # 함수
            # fix(X,y) : Fit linear model
            # get_params(self, deep=True) : Get parameters for this estimator.
            # predict(self, X) : Predict using the linear model
            # score(self, X, y, sample_weight=None) : Returns the coefficient of determination R^2 of the prediction.
            # set_params(self, **params) : Set the parameters of this estimator.

            # 사이킷런 사용
            poly_features = PolynomialFeatures(degree=3, include_bias=False)
            x_train_poly = poly_features.fit_transform(x_train)
            # 모델생성
            poly_model_s = LinearRegression()
            poly_model_h = LinearRegression()
            poly_model_l = LinearRegression()
            poly_model_c = LinearRegression()
            # 모델훈련
            poly_model_s.fit(x_train_poly, y_start)
            poly_model_h.fit(x_train_poly, y_high)
            poly_model_l.fit(x_train_poly, y_low)
            poly_model_c.fit(x_train_poly, y_close)

            # 사이킷런 사용
            X_new_poly = poly_features.transform(x_train)
            poly_pred_s = poly_model_s.predict(X_new_poly)
            poly_pred_h = poly_model_h.predict(X_new_poly)
            poly_pred_l = poly_model_l.predict(X_new_poly)
            poly_pred_c = poly_model_c.predict(X_new_poly)

            stock_price_day_cnt_2cha = [[stock_price_candle_cnt]]
            new_stock_price_day_cnt_2cha = poly_features.transform(stock_price_day_cnt_2cha)
            poly_pred_twenty_h = poly_model_h.predict(new_stock_price_day_cnt_2cha)
            poly_pred_twenty_l = poly_model_l.predict(new_stock_price_day_cnt_2cha)
            # print(poly_pred_h)
            # print(poly_pred_twenty_h)
            # print(poly_pred_l)
            # print(poly_pred_twenty_l)

            # poly_model_c.intercept_, poly_model_c.coef_
            # 절편
            # print(poly_model_h.intercept_)
            # print(poly_model_l.intercept_)
            # 기울기
            poly_h_gradient = poly_model_h.coef_
            poly_l_gradient = poly_model_l.coef_
            # print(poly_h_gradient)
            # print(poly_l_gradient)

            # 모델생성
            line_model_s = LinearRegression()
            line_model_h = LinearRegression()
            line_model_l = LinearRegression()
            line_model_c = LinearRegression()
            # 모델훈련
            line_model_s.fit(x_train, y_s)
            line_model_h.fit(x_train, y_h)
            line_model_l.fit(x_train, y_l)
            line_model_c.fit(x_train, y_c)
            # 예상하기
            line_pred_s = line_model_s.predict(x_train)
            line_pred_h = line_model_h.predict(x_train)
            line_pred_l = line_model_l.predict(x_train)
            line_pred_c = line_model_c.predict(x_train)

            line_pred_twenty_h = line_model_h.predict([[stock_price_candle_cnt]])
            line_pred_twenty_l = line_model_l.predict([[stock_price_candle_cnt]])
            # print(line_pred_h)
            # print(line_pred_twenty_h)
            # print(line_pred_l)
            # print(line_pred_twenty_l)

            # 추세선 기준 고가/저가 구하고 최대값 최소값 구하기
            poly_pred_high_diff_price = []
            poly_pred_low_diff_price = []
            pred_high_diff_price = []
            pred_low_diff_price = []
            for i in range(stock_price_candle_cnt):
                # poly
                poly_pred_high_diff_price.append(stock_high[i] - poly_pred_h[i][-1])
                # print(stock_high[i])
                # print(poly_pred_h[i])
                poly_pred_low_diff_price.append(poly_pred_l[i][-1] - stock_low[i])
                poly_pred_nineteen_h = poly_pred_h[i][-1]
                poly_pred_nineteen_l = poly_pred_l[i][-1]

                # 위에서 인덱스를 뒤집었으므로 꺼꾸로 계산
                pred_high_diff_price.append(y_h[(stock_price_candle_cnt - 1 + min_index) - i] - line_pred_h[i])
                # print(y_h[(stock_price_candle_cnt - 1 + min_index) - i])
                # print(line_pred_h[i])
                pred_low_diff_price.append(line_pred_l[i] - y_l[(stock_price_candle_cnt - 1 + min_index) - i])
                line_pred_nineteen_h = line_pred_h[i]
                line_pred_nineteen_l = line_pred_l[i]
            # print(poly_pred_high_diff_price)
            # print(poly_pred_low_diff_price)
            poly_pred_high_diff_price_max = max(poly_pred_high_diff_price)
            poly_pred_low_diff_price_max = max(poly_pred_low_diff_price)
            pred_high_diff_price_max = max(pred_high_diff_price)
            pred_low_diff_price_max = max(pred_low_diff_price)
            # 추세선 기준으로 고가 혹은 저가와의 차이 최대값
            # print(poly_pred_high_diff_price_max)
            # print(poly_pred_low_diff_price_max)
            # print(pred_high_diff_price_max)
            # print(pred_low_diff_price_max)
            # 매도최대값 / 매수최저값
            # print(poly_pred_nineteen_h)
            # print(poly_pred_nineteen_l)
            # print(line_pred_nineteen_h)
            # print(line_pred_nineteen_l)
            poly_sell_max_price = poly_pred_nineteen_h + poly_pred_high_diff_price_max
            poly_buy_min_price = poly_pred_nineteen_l - poly_pred_low_diff_price_max
            sell_max_price = line_pred_nineteen_h + pred_high_diff_price_max
            buy_min_price = line_pred_nineteen_l - pred_low_diff_price_max
            # print(poly_sell_max_price)
            # print(poly_buy_min_price)
            poly_sell_max_price_for_graph = []
            poly_buy_min_price_for_graph = []
            for i in range(stock_price_candle_cnt):
                # max/min 그래프 그리는 용
                poly_sell_max_price_for_graph.append(poly_sell_max_price)
                poly_buy_min_price_for_graph.append(poly_buy_min_price)
            # print(sell_max_price)
            # print(buy_min_price)
            # 기울기
            line_h_gradient = line_model_h.coef_
            line_l_gradient = line_model_l.coef_
            # print(line_h_gradient)
            # print(line_l_gradient)

            # 값구하기(일봉 max/min 비교)
            if (running_y_h >= poly_sell_max_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(1)
                day_market_sell_buy_time['buy_mode'].append(0)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
            elif (running_y_l <= poly_buy_min_price):
                day_market_sell_buy_time['running_stock_date'].append(running_stock_date)
                day_market_sell_buy_time['running_y_h'].append(running_y_h)
                day_market_sell_buy_time['running_y_l'].append(running_y_l)
                day_market_sell_buy_time['sell_mode'].append(0)
                day_market_sell_buy_time['buy_mode'].append(1)
                day_market_sell_buy_time['poly_h_gradient'].append(poly_h_gradient[-1][-1])
                day_market_sell_buy_time['poly_l_gradient'].append(poly_l_gradient[-1][-1])
                day_market_sell_buy_time['poly_sell_max_price'].append(poly_sell_max_price)
                day_market_sell_buy_time['poly_buy_min_price'].append(poly_buy_min_price)
        # print(day_market_sell_buy_time)

    # db닫기
    con.commit()
    con.close()

    # 저장
    df = pd.DataFrame(day_market_sell_buy_time,
                      columns=['running_y_h', 'running_y_l', 'sell_mode', 'buy_mode',
                               'poly_h_gradient', 'poly_l_gradient', 'poly_sell_max_price', 'poly_buy_min_price'],
                      index=day_market_sell_buy_time['running_stock_date'])

    con = sqlite3.connect(db_file_path + '/' + put_db_name)
    df.to_sql(current_today, con, if_exists='replace', index_label='deal_day')
    # 'append'는 테이블이 존재하면 데이터만을 추가
    # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
    # index_label	인덱스 칼럼에 대한 라벨을 지정


if __name__ == "__main__":
    import os

    # db 저장폴더
    Folder_Name_DB_Store = 'db_store'

    # # 장마감 c 이후
    #
    # # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    # # API에서 지난 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    # # 폴더명용
    # current_year = datetime.datetime.today().strftime("%Y")
    current_today = datetime.datetime.today().strftime("%Y%m%d")
    #
    # # 텍스트파일명용
    # choice_stock_filename = 'favorites_item_list'
    # # db명 설정(월봉 / 일봉)
    # db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_month' + '.db'
    # db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_day' + '.db'
    # # print(db_name_db_month)
    # # print(db_name_db_day)
    # self.stock_shlc_store_for_ai_fn(current_today, choice_stock_filename, db_name_db_month, db_name_db_day)

    # 연결선물
    # 선물옵션일차트요청
    future_s_code = '10100000'

    db_name_db_day = Folder_Name_DB_Store + '/' + 'test' + '.db'

    con = sqlite3.connect(db_name_db_day)
    df_read = pd.read_sql("SELECT * FROM " + "'" + future_s_code + "'", con, index_col=None)
    # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
    # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당

    print(df_read.iloc[0]['stock_date'])
    type(df_read.iloc[0]['stock_date'])

    print(df_read)

    if str(current_today) == df_read.iloc[0]['stock_date']:
        print('today is already')

    df_read.drop([0, 0], axis=0, inplace=True)

    new_row = pd.DataFrame([['aaa', 555, 666, 777, 888]], columns=df_read.columns)

    new_df = pd.concat([df_read.iloc[:0], new_row, df_read.iloc[0:]], ignore_index=True)


    print(new_df)



