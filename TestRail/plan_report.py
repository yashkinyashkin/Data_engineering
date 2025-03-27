import pandas as pd
import re
import config
from classes import *

# ID Plan в котором будет создаваться отчёт
testrail_plan_id = config.plan_id


client = APIClient(config.client)
client.user = config.user
client.password = config.password


testrail = TestRailProject(client=client, project_id=27)
testrail.plan.select(testrail_plan_id)


def elapsed_to_sec_convert(elapsed_time: str) -> int:
    """Функция для перевода времени из формата принятого на TestRail в секунды"""
    sum_sec = 0
    if elapsed_time:
        split_time_list = elapsed_time.split(' ')
    else:
        split_time_list = ['']
    for item in split_time_list:
        if 's' in item:
            sum_sec += int(re.sub('\D', '', item))
        if 'm' in item:
            sum_sec += int(re.sub('\D', '', item))*60
        if 'h' in item:
            sum_sec += int(re.sub('\D', '', item))*3600
    return sum_sec


def create_testrail_table(df: pd.DataFrame) -> str:
    """Переводит DataFrame в текстовое представление таблицы на TestRail"""
    text_table = ''
    columns = df.columns
    columns_str = '||'
    for column in columns:
        columns_str += f'|:{column}'
    text_table += f'{columns_str}\n'

    for row in df.itertuples(index=False):
        row_str = '|'
        for value in row:
            row_str += f'|{value}'
        text_table += f'{row_str}\n'

    return text_table


def seconds_to_timespan(total_seconds):
    """Переводит секунды в h m s строку"""
    if total_seconds:
        timespan = ''
        hours = total_seconds // 3600
        remaining_sec = total_seconds - (hours * 3600)
        minutes = remaining_sec // 60
        sec = remaining_sec - (minutes * 60)
        if hours:
            timespan += f'{int(hours)}h'
        if minutes:
            timespan += f' {int(minutes)}m'
        if sec:
            timespan += f' {int(sec)}s'
        return timespan
    else:
        return '0s'


def add_sum_and_percent_df(data_frame: pd.DataFrame,convert_time:bool = False):
    # Группируем значения по серийному номеру ATM
    data_frame = data_frame.groupby(['Серийный номер ATM']).sum()

    # Получаем сумму времени выполнения во всех тестов
    sum_table = pd.DataFrame(data_frame.sum()).transpose()
    sum_table.astype('int')

    # Получаем процент от времени
    percent_table = sum_table.copy()
    max_value = sum_table.max().max()
    percent_table.astype('str')
    for value in percent_table:
        percent = round(sum_table[value].sum()/max_value*100, 2)
        percent_table[value] = f'{percent} %'

    # Переводим время из секунд в "0h 0m 0s" представление
    if convert_time:
        data_frame.astype('int')
        for column in data_frame:
            data_frame[column] = data_frame[column].apply(seconds_to_timespan)
            sum_table[column] = sum_table[column].apply(seconds_to_timespan)

    # Переводим индекс atm_serial в отдельный столбец
    data_frame.reset_index(inplace = True)

    # Добавляем заголовки для суммы и процентов
    sum_table['Серийный номер ATM'] = 'Сумма'
    percent_table['Серийный номер ATM'] = 'Процент'

    # Собираем все вместе
    data_frame = pd.concat([data_frame, sum_table, percent_table])

    # Дополнительно переводим столбцы в тип str, чтобы избавиться от точек в конце
    data_frame = data_frame.astype('str')

    return data_frame


atm_devices_runs = []
counter = 0
max_counter = len(testrail.plan.information["entries"])

# Переменные для подсчёта не табличных данных
all_results_count = 0 # Общее число результатов на TestRail
very_failed_count = 0 # Тесты упавшие более двух раз
untested_cases_list = [] # Тесты со статусом Untested, которые должны войти в итоговую статистику

# Получаем список всех entry и собираем с них всю необходимую информацию
for entry in testrail.plan.information["entries"]:
    counter += 1
    print(f"Обработка прогона {counter} из {max_counter}")
    # Получаем список всех Run
    for run in entry['runs']:

        run_info_dict = {}
        atm_serial = 'ATM serial: Неизвестен'
        # Добавляем в словарь ключ по серийному номеру ATM
        if run['description']:
            for line in run['description'].split('\n'):
                if 'ATM_MB' in line:
                    atm_serial = line
        run_info_dict['atm_serial'] = atm_serial

        # Преобразуем результаты тестов Run в таблицу pandas
        results_data_frame = pd.DataFrame(testrail.run.get_results_for_run(run['id']))
        run_info_dict['name'] = run['name']
        # Приблизительное время отправки результатов на TestRail(количество отправок результатов * 3.5 сек)
        run_info_dict['send_result_time'] = len(results_data_frame['id']) * 3.5
        # Получаем сумму времени по всему Run
        run_info_dict['elapsed'] = results_data_frame['elapsed'].apply(elapsed_to_sec_convert).sum() + run_info_dict['send_result_time'] # Общее время
        run_info_dict['downtime'] = results_data_frame['custom_downtime'].apply(elapsed_to_sec_convert).sum() # Время простоя
        run_info_dict['dev_wait'] = results_data_frame['custom_dev_wait'].apply(elapsed_to_sec_convert).sum() # Время ожидания устройств на связи
        run_info_dict['settings_loading_time'] = results_data_frame['custom_settings_loading_time'].apply(elapsed_to_sec_convert).sum() # Время загрузки настроек
        run_info_dict['base_state_time'] = results_data_frame['custom_base_state_time'].apply(elapsed_to_sec_convert).sum() # Время перехода в базовое состояние
        run_info_dict['test_time'] = run_info_dict['elapsed'] - run_info_dict['downtime']\
                                                              - run_info_dict['dev_wait']\
                                                              - run_info_dict['settings_loading_time']\
                                                              - run_info_dict['base_state_time']\
                                                              - run_info_dict['send_result_time'] # Время выполнения теста
        # Получаем список тестов, которые тестировались более 2-х раз
        tests_one_more_counts = pd.DataFrame(results_data_frame['test_id'].value_counts()[results_data_frame['test_id'].value_counts() > 1]).reset_index()
        # Получаем список тестов в которых было больше одного Fail
        fail_list = []
        for test in tests_one_more_counts['test_id']:
            error_count = len(results_data_frame[(results_data_frame['test_id'] == test) & (results_data_frame['status_id'] == 5)])
            if error_count > 1:
                fail_list.append(test)
        run_info_dict['very_failed_count'] = len(fail_list)

        # Подсчитываем общее количество тестов
        tests_data_frame = pd.DataFrame(testrail.plan.run.get_tests(run['id']))
        run_info_dict['all_tests_count'] = len(tests_data_frame)
        # Получаем список количества всех окончательных результатов тестов
        for info in run:
            if 'count' in info:
                run_info_dict[info] = run[info]

        atm_devices_runs.append(run_info_dict)

        # Удаление результатов со статусом Blocked и тесты которые не помечены как автоматизированные
        tests_list = testrail.plan.run.get_tests(run['id'])
        new_cases_list = []
        for test_info in tests_list:
            if test_info['status_id'] != 2 and test_info["custom_automatization"] is True:
                new_cases_list.append(test_info['case_id'])
                if test_info['status_id'] == 3:
                    untested_cases_list.append(test_info['case_id'])

        # Переменные для подсчёта не табличных данных
        all_results_count += len(new_cases_list)
        very_failed_count += len(fail_list)

        if untested_cases_list:
            print("\u001b[31m")
            print('Run не будет обновлён, пока все тесты не будут протестированы!')
            print("\u001b[0m")
            continue

        # Получаем description из Run поскольку иначе оно будет утеряно
        run_description = testrail.run.get(run['id'])['description']
        testrail.plan.update_plan_entry(entry_id=entry['id'], name=run['name'], include_all=False, case_ids=new_cases_list, description=run_description)


# Создаём основную таблицу по времени выполнения
atm_time_table = pd.DataFrame(atm_devices_runs)
# Выбираем нужные нам столбцы
atm_time_table = atm_time_table[['atm_serial',
                                 'settings_loading_time' ,
                                 'downtime' ,
                                 'send_result_time',
                                 'dev_wait',
                                 'base_state_time',
                                 'test_time',
                                 'elapsed',
                                 ]]

# Переименовываем столбцы
atm_time_table.rename(columns = {'atm_serial': 'Серийный номер ATM',
                                 'elapsed':'Общее время выполнения',
                                 'settings_loading_time':'Время загрузки настроек',
                                 'downtime':'Время простоя',
                                 'send_result_time':'Время отправки результатов',
                                 'base_state_time': "Время переходов в базовое состояние",
                                 'dev_wait':'Время ожидания устройств на связи',
                                 'test_time': "Время прохождения тестов",
                                 },
                           inplace=True
                           )

# Фиксируем максимальное время выполнения тестов для одного ОБ
max_time_one_block = atm_time_table['Общее время выполнения'].max()
# Добавляем строки суммы и количества процентов
atm_time_table = add_sum_and_percent_df(atm_time_table, convert_time=True)
# Переводим DataFrame в строчное представление таблиц на TestRail
time_testrail_table_str = create_testrail_table(atm_time_table)

# Создаём основную таблицу с результатами тестов
atm_tests_count_table = pd.DataFrame(atm_devices_runs)
# Выбираем нужные нам столбцы
atm_tests_count_table = atm_tests_count_table[['atm_serial',
                                               'blocked_count',
                                               'failed_count',
                                               'passed_count',
                                               'retest_count',
                                               'untested_count',
                                               'very_failed_count',
                                               'all_tests_count',
                                                ]]
# Переименовываем столбцы
atm_tests_count_table.rename(columns = {'atm_serial': 'Серийный номер ATM',
                                        'blocked_count':'Заблокированные тесты',
                                        'failed_count':'Не прошедшие тесты',
                                        'passed_count':'Прошедшие тесты',
                                        'retest_count':'Прошедшие не с первого предъявления',
                                        'untested_count':'Не протестированные',
                                        'very_failed_count':'Более 2-х ошибок в тесте',
                                        'all_tests_count':'Общее число тестов',
                                 },
                           inplace=True
                           )
# Добавляем строки суммы и количества процентов
atm_tests_count_table = add_sum_and_percent_df(atm_tests_count_table)

# Переводим DataFrame в строчное представление таблиц на TestRail
tests_count_table_str = create_testrail_table(atm_tests_count_table)

# Создаём текст описания для отправки на TestRail
text = f"""# Затраченное время:\n{time_testrail_table_str}

## Максимальная длительность проверки одного ОБ: {seconds_to_timespan(max_time_one_block)}

---

# Количество выполненных тестов:
{tests_count_table_str}

## Процент тестов, в которых более 2-х ошибок: {str(round(very_failed_count/all_results_count*100, 2)).replace('.', ',')} %"""

if not untested_cases_list:
    # Добавляем текст в описание Plan а TestRail
    testrail.plan.update(data={'description': text})
    # Закрываем Plan на TestRail
    testrail.plan.close()
else:
    print("\u001b[31m")
    print(f"В TestPlan есть тесты без результата тестирования({len(untested_cases_list)} штук)")
    print(f'Список тестов: {untested_cases_list}\n')
    print('!!!   -------------------------------------------------   !!!')
    print('План не будет закрыт, пока все тесты не будут протестированы!')
    print('!!!   -------------------------------------------------   !!!')
    print("\u001b[0m")


