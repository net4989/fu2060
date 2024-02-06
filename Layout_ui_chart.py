import sys
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import sqlite3
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

# 최빈값(가장 빈번하게 관찰/측정되는 값)
from scipy.stats import mode



form_class = uic.loadUiType("k200_auto_layout.ui")[0]



class Layout(QMainWindow, form_class):
    # def __init__(self):
    #     super().__init__()

        # form_class를 상속받았기 때문에 form_class에 정의돼 있던 속성이나 메서드를 모두 상속받게 됩니다.
        # 따라서 다음과 같이 setupUi 메서드를 호출함으로써 Qt Designer를 통해 구성한 UI를 화면에 출력할 수 있습니다.
        # 참고로 setupUi라는 메서드 이름은 정해진 이름이기 때문에 그대로 사용
        # 버튼 객체에 대한 생성 및 바인딩은 setupUi 메서드에서 수행
        # self.setupUi(self)

        # 메인윈도창 레이아웃 셋팅(차트)
        # self.layout_chart_draw()

    # 메인윈도창 레이아웃 셋팅(차트)
    def layout_chart_draw(self):
        self.setGeometry(10, 50, 1440, 900)
        # self.setWindowTitle('K200_Auto_Order v0.2(layout_20181223)')
        # self.setWindowTitle('K200_Auto_Order v0.21(layout_class상속_20181224)')
        self.setWindowIcon(QIcon('icon.png'))

        ## Data Pickup
        # 레이아웃 생성
        layout_monthmalldata = QGridLayout()
        # 레이아웃에 위젯 추가
        layout_monthmalldata.addWidget(self.pushButton_datapickup_future_s_M, 1, 0)
        layout_monthmalldata.addWidget(self.comboBox_future_s_chain_month, 1, 1)
        layout_monthmalldata.addWidget(self.pushButton_datapickup_code_s_D, 2, 0)
        layout_monthmalldata.addWidget(self.comboBox_date_s_day, 2, 1)
        layout_monthmalldata.addWidget(self.comboBox_code_s_day, 3, 0)
        layout_monthmalldata.addWidget(self.checkbox_today_x, 3, 1)
        layout_monthmalldata.addWidget(self.radioButton_20, 4, 0)
        layout_monthmalldata.addWidget(self.radioButton_60, 4, 1)
        layout_monthmalldata.addWidget(self.radioButton_30, 5, 0)
        layout_monthmalldata.addWidget(self.radioButton_40, 5, 1)

        layout_monthmalldata.addWidget(self.pushButton_datapickup, 6, 0)
        layout_monthmalldata.addWidget(self.checkbox_realtime, 6, 1)
        layout_monthmalldata.addWidget(self.comboBox_year, 7, 0)
        layout_monthmalldata.addWidget(self.comboBox_monthmall, 7, 1)
        layout_monthmalldata.addWidget(self.comboBox_date, 8, 0)
        layout_monthmalldata.addWidget(self.comboBox_time, 8, 1)
        # 그룹박스에 setLayout
        self.groupbox_datapickup.setLayout(layout_monthmalldata)


        ## 테이블 위젯
        # 옵션시세표
        self.tableWidget_optionprice.resizeColumnsToContents()
        self.tableWidget_optionprice.resizeRowsToContents()


        # ## Cross
        # # 레이아웃 생성
        # layout_cross = QGridLayout()
        # # layout_cross.setColumnStretch(1, 4)
        # # layout_cross.setColumnStretch(2, 4)
        # # 레이아웃에 위젯 추가
        # layout_cross.addWidget(self.button_crosscheck_0, 1, 0)
        # layout_cross.addWidget(self.button_crosscheck_1, 2, 0)
        # layout_cross.addWidget(self.button_crosscheck_2, 3, 0)
        # layout_cross.addWidget(self.button_crosscheck_3, 4, 0)
        #
        # layout_cross.addWidget(self.button_crosscheck_44, 1, 1)
        # layout_cross.addWidget(self.button_crosscheck_4, 2, 1)
        # layout_cross.addWidget(self.button_crosscheck_5, 3, 1)
        # layout_cross.addWidget(self.button_crosscheck_6, 4, 1)
        # layout_cross.addWidget(self.button_crosscheck_88, 5, 1)
        #
        # layout_cross.addWidget(self.button_crosscheck_7, 2, 2)
        # layout_cross.addWidget(self.button_crosscheck_8, 3, 2)
        # layout_cross.addWidget(self.button_crosscheck_9, 4, 2)
        # layout_cross.addWidget(self.button_crosscheck_10, 5, 2)
        #
        # # 그룹박스에 setLayout
        # self.groupBox_cross.setLayout(layout_cross)


        # ## Basic_Choice
        # # 레이아웃 생성
        # layout_basic_choice = QGridLayout()
        # # 레이아웃에 위젯 추가
        # layout_basic_choice.addWidget(self.pushButton_timer1sec_5sec, 1, 0)
        # layout_basic_choice.addWidget(self.spinBox_timer1sec_5sec, 1, 1)
        # layout_basic_choice.addWidget(self.pushButton_full_or_half_store, 2, 0)
        # layout_basic_choice.addWidget(self.radioButton_future_s, 2, 1)
        # layout_basic_choice.addWidget(self.radioButton_k200_s, 3, 0)
        # layout_basic_choice.addWidget(self.radioButton_k100_s, 3, 1)
        # layout_basic_choice.addWidget(self.radioButton_krx_s, 4, 0)
        # layout_basic_choice.addWidget(self.radioButton_kospi_s, 4, 1)
        #
        # # 그룹박스에 setLayout
        # self.groupBox_basic_choice.setLayout(layout_basic_choice)


        ## Order
        # 레이아웃 생성
        layout_order = QGridLayout()
        # 레이아웃에 위젯 추가
        layout_order.addWidget(self.comboBox_acc_stock, 1, 0)
        layout_order.addWidget(self.comboBox_acc, 1, 1)
        layout_order.addWidget(self.pushButton_myhave, 2, 0)
        layout_order.addWidget(self.pushButton_auto_order, 2, 1)
        layout_order.addWidget(self.pushButton_fu_buy_have, 3, 0)
        layout_order.addWidget(self.pushButton_fu_sell_have, 3, 1)
        layout_order.addWidget(self.pushButton_callhave, 4, 0)
        layout_order.addWidget(self.pushButton_puthave, 4, 1)
        layout_order.addWidget(self.pushButton_market_start_3, 5, 0)
        layout_order.addWidget(self.pushButton_market_ending_c, 5, 1)
        layout_order.addWidget(self.progressBar_power, 6, 0)
        layout_order.addWidget(self.progressBar_order, 6, 1)

        # 그룹박스에 setLayout
        self.groupBox_order.setLayout(layout_order)

        ## menuLayout(부모 레이아웃)
        self.menuLayout.addStretch(1)

        # figsize라는 인자를 통해 Figure 객체의 크기를 조정
        self.fig = plt.figure(figsize=(12, 8))
        #  FigureCanvas 객체를 생성
        self.canvas = FigureCanvas(self.fig)

        ## chartLayout(부모 레이아웃)
        self.chartLayout.addWidget(self.canvas)

        ## 최상단 레이아웃
        # layout = QHBoxLayout()
        self.layout.addLayout(self.menuLayout)
        self.layout.addLayout(self.chartLayout)

        self.layout.setStretchFactor(self.menuLayout, 0)
        self.layout.setStretchFactor(self.chartLayout, 1)

        self.setLayout(self.layout)

    # 차트 그리기
    def draw_chart(self, table_name_today, df_read, min_index, chart_ylim, Up_CenterOption_Down):
        self.fig.clear()
        self.top_axes = self.fig.add_subplot(1, 1, 1)
        # self.bottom_axes = self.fig.add_subplot(2, 1, 2)
        self.top_axes.set_title(table_name_today)

        # self.top_axes = self.fig.subplot2grid((4, 4), (0, 0), rowspan=3, colspan=4)
        # self.bottom_axes = self.fig.subplot2grid((4, 4), (3, 0), rowspan=1, colspan=4)
        # self.bottom_axes.get_yaxis().get_major_formatter().set_scientific(False)

        # new_df_read = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down - 2 + min_index])]
        # self.top_axes.plot(new_df_read.index + 2, new_df_read['call_run_price'], 'r', label=new_df_read['option_price'][Up_CenterOption_Down - 2 + min_index])
        # self.top_axes.plot(new_df_read.index + 2, new_df_read['put_run_price'], 'b', label=new_df_read['option_price'][Up_CenterOption_Down - 2 + min_index])

        new_df_read = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down - 1 + min_index])]
        self.top_axes.plot(new_df_read.index + 1, new_df_read['call_run_price'], 'r:', label=new_df_read['option_price'][Up_CenterOption_Down - 1 + min_index])
        self.top_axes.plot(new_df_read.index + 1, new_df_read['put_run_price'], 'b:', label=new_df_read['option_price'][Up_CenterOption_Down - 1 + min_index])

        # 중심가
        new_df_read = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down + 0 + min_index])]
        self.top_axes.plot(new_df_read.index + 0, new_df_read['call_run_price'], 'r', label=new_df_read['option_price'][Up_CenterOption_Down + 0 + min_index])
        self.top_axes.plot(new_df_read.index + 0, new_df_read['put_run_price'], 'b', label=new_df_read['option_price'][Up_CenterOption_Down + 0 + min_index])

        new_df_read = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down + 1 + min_index])]
        self.top_axes.plot(new_df_read.index - 1, new_df_read['call_run_price'], 'r:', label=new_df_read['option_price'][Up_CenterOption_Down + 1 + min_index])
        self.top_axes.plot(new_df_read.index - 1, new_df_read['put_run_price'], 'b:', label=new_df_read['option_price'][Up_CenterOption_Down + 1 + min_index])

        # new_df_read = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down + 2 + min_index])]
        # self.top_axes.plot(new_df_read.index - 2, new_df_read['call_run_price'], 'r', label=new_df_read['option_price'][Up_CenterOption_Down + 2 + min_index])
        # self.top_axes.plot(new_df_read.index - 2, new_df_read['put_run_price'], 'b', label=new_df_read['option_price'][Up_CenterOption_Down + 2 + min_index])

        # print(len(new_df_read['time']))
        # print(new_df_read['time'])

        time_str_labels = []
        for time_data in (new_df_read['time']):
            time_str_labels.append(time_data[:5])
        # print(new_df_read.index)
        # print(time_str_labels)
        time_str_label = []
        for i in range(len(time_str_labels)):
            if i == 0:
                time_str_label.append(time_str_labels[i][:5])
            elif time_str_labels[i][:2] == time_str_labels[i - 1][:2]:
                # time_str_label.append(time_str_labels[i][3:5])
                time_str_label.append('')
            else:
                time_str_label.append(time_str_labels[i][:5])
        # print(time_str_label)
        self.top_axes.set(xticks=new_df_read.index, xticklabels=time_str_label)

        plt.tight_layout()
        plt.ylim(0, chart_ylim)

        # Show the major grid lines with dark grey lines
        plt.grid(b=True, which='major', color='#999999', linestyle='-')
        # Show the minor grid lines with very faint and almost transparent grey lines
        plt.minorticks_on()
        plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)

        plt.legend(loc='upper left')

        self.canvas.draw()

    # 차트 그리기::선물 real poly
    def draw_chart_future_s_real_poly(self, table_name_today, df_read, min_index, chart_ylim, Up_CenterOption_Down):
        self.fig.clear()
        self.top_axes = self.fig.add_subplot(1, 1, 1)
        # self.bottom_axes = self.fig.add_subplot(2, 1, 2)
        self.top_axes.set_title(table_name_today)

        # pd 필요 중심가 취하고
        df_read_use = df_read[df_read['option_price'] == (df_read['option_price'][Up_CenterOption_Down + 0 + min_index])]
        # x_train
        x_index_np = np.array(df_read_use.index)
        # print(x_index_np)
        # x_index_np 2차원 array 형태로 변경
        x_train = x_index_np.reshape(-1, 1)
        # print(x_train)

        # y_train
        future_s_run_price = df_read_use['future_s'].values
        # print(future_s_run_price)
        y_train = future_s_run_price.reshape(-1, 1)
        # print(y_train)
        # print('x_train.shape : ', x_train.shape)
        # print('y_train.shape : ', y_train.shape)

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
        poly_model_future_s = LinearRegression()
        # 모델훈련
        poly_model_future_s.fit(x_train_poly, y_train)
        # 사이킷런 사용
        X_new_poly = poly_features.transform(x_train)
        poly_pred_future_s = poly_model_future_s.predict(X_new_poly)
        # print(poly_pred_future_s)

        # poly_model_c.intercept_, poly_model_c.coef_
        # 절편
        # print(poly_model_future_s.intercept_)
        # 기울기
        poly_future_s_gradient = poly_model_future_s.coef_
        # print(poly_future_s_gradient)

        # # 추세선 기준 고가/저가 구하고 최대값 최소값 구하기
        # poly_pred_high_diff_price = []
        # poly_pred_low_diff_price = []
        # for x in range(len(x_train)):
        #     # print(x)
        #     # print(future_s_run_price[x])
        #     # print(poly_pred_future_s[x][0])
        #     # print('-----')
        #     if poly_pred_future_s[x][0] < future_s_run_price[x]:
        #         poly_pred_high_diff_price.append(future_s_run_price[x] - poly_pred_future_s[x][0])
        #     elif poly_pred_future_s[x][0] > future_s_run_price[x]:
        #         poly_pred_low_diff_price.append(poly_pred_future_s[x][0] - future_s_run_price[x])
        # # 장초반시에 한쪽으로 몰릴수가 있음
        # if len(poly_pred_high_diff_price) == 0:
        #     poly_pred_high_diff_price.append(poly_pred_future_s[-1][0] - future_s_run_price[-1])
        # if len(poly_pred_low_diff_price) == 0:
        #     poly_pred_low_diff_price.append(future_s_run_price[-1] - poly_pred_future_s[-1][0])
        # # print(poly_pred_high_diff_price)
        # # print(poly_pred_low_diff_price)
        # poly_pred_high_diff_price_max = max(poly_pred_high_diff_price)
        # poly_pred_low_diff_price_max = max(poly_pred_low_diff_price)
        # poly_pred_high_diff_price_ave = np.mean(poly_pred_high_diff_price)
        # poly_pred_low_diff_price_ave = np.mean(poly_pred_low_diff_price)
        # poly_pred_high_diff_price_median = np.median(poly_pred_high_diff_price)
        # poly_pred_low_diff_price_median = np.median(poly_pred_low_diff_price)
        # poly_pred_high_diff_price_std = np.std(poly_pred_high_diff_price)
        # poly_pred_low_diff_price_std = np.std(poly_pred_low_diff_price)
        # poly_pred_high_diff_price_final = poly_pred_high_diff_price_median + poly_pred_high_diff_price_std
        # poly_pred_low_diff_price_final = poly_pred_low_diff_price_median + poly_pred_low_diff_price_std
        # # 추세선 기준으로 고가 혹은 저가와의 차이 최대값
        # print(poly_pred_high_diff_price_max)
        # print(poly_pred_low_diff_price_max)
        # # 추세선 기준으로 고가 혹은 저가와의 차이 평균값
        # print(poly_pred_high_diff_price_ave)
        # print(poly_pred_low_diff_price_ave)
        # # 추세선 기준으로 고가 혹은 저가와의 차이 중앙값
        # print(poly_pred_high_diff_price_median)
        # print(poly_pred_low_diff_price_median)
        # # 추세선 기준으로 고가 혹은 저가와의 차이 표준편차
        # print(poly_pred_high_diff_price_std)
        # print(poly_pred_low_diff_price_std)
        # # 추세선 기준으로 고가 혹은 저가와의 차이 중앙값에서 표준편차를 더한값
        # print(poly_pred_high_diff_price_final)
        # print(poly_pred_low_diff_price_final)
        # 선물 마지막값
        future_s_run_price_last = future_s_run_price[-1]
        # print(future_s_run_price_last)
        # # 매도타임 최대값/매수타임 최소값
        # future_s_sell_time_max_price = future_s_run_price_last + poly_pred_high_diff_price_max
        # future_s_buy_time_min_price = future_s_run_price_last - poly_pred_low_diff_price_max
        # future_s_sell_time_ave_price = future_s_run_price_last + poly_pred_high_diff_price_ave
        # future_s_buy_time_ave_price = future_s_run_price_last - poly_pred_low_diff_price_ave
        # future_s_sell_time_final_price = future_s_run_price_last + poly_pred_high_diff_price_final
        # future_s_buy_time_final_price = future_s_run_price_last - poly_pred_low_diff_price_final
        # print(future_s_sell_time_final_price)
        # print(future_s_buy_time_final_price)

        # 모델생성(1차원)
        line_model_future_s = LinearRegression()
        # 모델훈련
        line_model_future_s.fit(x_train, y_train)
        # 예상하기
        line_pred_future_s = line_model_future_s.predict(x_train)
        # print(line_pred_future_s)
        # 기울기
        line_h_gradient = line_model_future_s.coef_
        # print(line_h_gradient)

        # 선물매도(콜옵션 헷징) / 선물매수(풋옵션 헷징) :: 기준 선물가 구하기(0.1% ~ 0.2%의 중간:: 0.15%))
        future_s_sell_time_max_price = future_s_run_price_last * 1.002
        future_s_sell_time_final_price = future_s_run_price_last * 1.0015
        future_s_buy_time_final_price = future_s_run_price_last * 0.9985
        future_s_buy_time_min_price = future_s_run_price_last * 0.998

        # =====
        # 선형 회귀 모델 표현¶
        # python의 plot을 이용하여 출력
        plt.axhline(future_s_sell_time_max_price, color='red', linestyle='--', linewidth=1,
                    label=future_s_sell_time_max_price)
        plt.axhline(future_s_sell_time_final_price, color='red', linestyle='-', linewidth=2,
                    label=future_s_sell_time_final_price)
        plt.plot(df_read_use.index, poly_pred_future_s, 'r-', label=poly_future_s_gradient)
        plt.axhline(future_s_run_price_last, color='magenta', linestyle=':', linewidth=2, label=future_s_run_price_last)
        plt.plot(df_read_use.index, line_pred_future_s, 'm-', label=line_h_gradient)
        plt.axhline(future_s_buy_time_final_price, color='blue', linestyle='-', linewidth=2,
                    label=future_s_buy_time_final_price)
        plt.axhline(future_s_buy_time_min_price, color='blue', linestyle='--', linewidth=1,
                    label=future_s_buy_time_min_price)
        # # 캔들
        plt.plot(df_read_use.index, y_train, 'm.')

        # X축
        time_str_labels = []
        for time_data in (df_read_use['time']):
            time_str_labels.append(time_data[:5])
        # print(new_df_read.index)
        # print(time_str_labels)
        time_str_label = []
        for i in range(len(time_str_labels)):
            if i == 0:
                time_str_label.append(time_str_labels[i][:5])
            elif time_str_labels[i][:2] == time_str_labels[i - 1][:2]:
                # time_str_label.append(time_str_labels[i][3:5])
                time_str_label.append('')
            else:
                time_str_label.append(time_str_labels[i][:5])
        # print(time_str_label)
        self.top_axes.set(xticks=df_read_use.index, xticklabels=time_str_label)

        plt.tight_layout()
        # Show the major grid lines with dark grey lines
        plt.grid(b=True, which='major', color='#999999', linestyle='-')
        # Show the minor grid lines with very faint and almost transparent grey lines
        plt.minorticks_on()
        plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)

        plt.legend()

        self.canvas.draw()

        # 매도타임 최대값/매수타임 최소값 전달
        return future_s_sell_time_final_price, future_s_buy_time_final_price, poly_future_s_gradient[0][-1]

    # 연결선물 그리기
    def draw_chart_gui_right(self, month_or_day, stock_date, df_read_use, min_index, table_name, stock_price_candle_cnt, futrue_s_run_price, futrue_s_start_price, futrue_s_high_price, futrue_s_low_price, checkbox_today_x):
        self.fig.clear()
        self.top_axes = self.fig.add_subplot(1, 1, 1)

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

        # print(sell_max_price)
        # print(buy_min_price)
        # 기울기
        line_h_gradient = line_model_h.coef_
        line_l_gradient = line_model_l.coef_
        # print(line_h_gradient)
        # print(line_l_gradient)

        # =====
        # 선형 회귀 모델 표현¶
        # python의 plot을 이용하여 출력
        plt.axhline(poly_sell_max_price, color='red', linestyle='-', linewidth=1, label=poly_sell_max_price)
        plt.plot(x_index, poly_pred_h, 'r-', label=poly_h_gradient)
        plt.plot(x_index, line_pred_h, 'm-', label=line_h_gradient)
        # plt.axhline(futrue_s_start_price, color='cyan', linestyle=':', linewidth=2)
        # plt.axhline(futrue_s_high_price, color='red', linestyle=':', linewidth=2)
        # plt.axhline(futrue_s_low_price, color='blue', linestyle=':', linewidth=2)
        # plt.axhline(futrue_s_run_price, color='magenta', linestyle=':', linewidth=2, label=futrue_s_run_price)
        plt.plot(x_index, line_pred_l, 'c-', label=line_l_gradient)
        plt.plot(x_index, poly_pred_l, 'b-', label=poly_l_gradient)
        plt.axhline(poly_buy_min_price, color='blue', linestyle='-', linewidth=1, label=poly_buy_min_price)
        # 캔들
        plt.plot(x_index, stock_start, 'c.')
        plt.plot(x_index, stock_high, 'r.')
        plt.plot(x_index, stock_low, 'b.')
        plt.plot(x_index, stock_close, 'm.')

        # -----
        # 당일 제외 차트를 그리느냐 / 아니냐
        if checkbox_today_x == True:
            # print(x_index)
            # print(x_index[-1] + 1)
            plt.plot((x_index[-1] + 1), futrue_s_start_price, 'c.')
            plt.plot((x_index[-1] + 1), futrue_s_high_price, 'r.')
            plt.plot((x_index[-1] + 1), futrue_s_low_price, 'b.')
            plt.plot((x_index[-1] + 1), futrue_s_run_price, 'm.')
        # -----

        # 월봉::X축
        if month_or_day == 'm':
            date_str_labels = []
            date_str_label = []
            for date_data in (df_read_use['stock_date']):
                date_str_labels.append(date_data[2:6])
            # print(df_read_use.index)
            # print(date_str_labels)
            for i in range(len(date_str_labels)):
                if i == 0:
                    date_str_label.append(date_str_labels[i])
                elif i == (len(date_str_labels) - 1):
                    date_str_label.append(date_str_labels[i])
                elif date_str_labels[i][:2] == date_str_labels[i - 1][:2]:
                    # date_str_label.append(date_str_labels[i][3:5])
                    date_str_label.append(date_str_labels[i][-2:])
                else:
                    date_str_label.append(date_str_labels[i])
            plt.title(table_name + ' : Month(' + stock_date[:6] + ')')
        # 일봉::X축
        elif month_or_day == 'd':
            date_str_labels = []
            date_str_label = []
            for date_data in (df_read_use['stock_date']):
                date_str_labels.append(date_data[-4:])
            # print(df_read_use.index)
            # print(date_str_labels)
            for i in range(len(date_str_labels)):
                if i == 0:
                    date_str_label.append(date_str_labels[i])
                elif i == (len(date_str_labels) - 1):
                    date_str_label.append(date_str_labels[i])
                elif date_str_labels[i][:2] == date_str_labels[i - 1][:2]:
                    # date_str_label.append(date_str_labels[i][3:5])
                    date_str_label.append(date_str_labels[i][-2:])
                else:
                    date_str_label.append(date_str_labels[i])
            plt.title(table_name + ' : Day(' + stock_date + ')')

        # print(date_str_label)
        self.top_axes.set(xticks=x_index, xticklabels=date_str_label)

        plt.tight_layout()
        # Show the major grid lines with dark grey lines
        plt.grid(b=True, which='major', color='#999999', linestyle='-')
        # Show the minor grid lines with very faint and almost transparent grey lines
        plt.minorticks_on()
        plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)

        # 범례표시
        plt.legend()

        # # plt.savefig() 함수에 파일 이름을 입력해주면 이미지 파일이 저장
        # plt.savefig('savefig_default.png')

        self.canvas.draw()

if __name__ == "__main__":


    import os
    import datetime

    from Data_store_pickup import *

    # db 저장폴더
    Folder_Name_DB_Store = 'db_store'

    # 종목코드 앞자리
    Global_Option_Item_Code_var = 'K200_k200_s'