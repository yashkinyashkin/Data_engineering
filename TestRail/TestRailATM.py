from classes import *


def milestones_name_create(firmware_version):
    """Генерация версии тестируемой ошибки"""
    return firmware_version


def testplan_name_create(suit_name, firmware_version):
    """Генерация названия тест-плана для TestRail"""
    return f'[{suit_name}] {firmware_version}'


def run_name_create(dev_id, dev_serial):
    """Генерация названия прогона для Тест Плана на TestRail"""
    dev_id = str(dev_id)
    dev_id = dev_id[:3] + '-' + dev_id[3:]
    return f'Dev-id: {dev_id} Serial: {dev_serial}'


def seconds_to_timespan(total_seconds):
    total_seconds = int(total_seconds)
    if total_seconds:
        hours = total_seconds // 3600
        remaining_sec = total_seconds - (hours * 3600)
        minutes = remaining_sec // 60
        sec = int(remaining_sec - (minutes * 60))

        return str(f"{hours}h {minutes}m {sec}s")
    else:
        return None


class TestRailCaseResultWriter:
    def __init__(self, suit_id: int, case_id: int, device_id: int, device_serial: str, firmware_version: str, project_id: int):
        self.__suit_id = suit_id
        self.__status = 'Untested'
        self.__case_id = case_id
        self.__project_id = project_id

        self.__dev_id = device_id
        self.__dev_serial = device_serial
        self.__firmware_version = firmware_version

        self.__client = APIClient('https://testrail.starline.ru/')
        self.__client.user = 'atmoir@starline.ru'
        self.__client.password = 'gfhjkmatmoir'

        self.__testrail = TestRailProject(client=self.__client, project_id=self.__project_id)

    def _check_testrail(self):
        """Проверка всех компонент необходимых для отправки результатов на TestRail"""

        def check_type_case_id():
            if isinstance(self.__case_id, int):
                self.__testrail.case.select(self.__case_id)
                return True
            else:
                raise TestPlanReportException(f"Название файла: {self.__case_id} - не является номером тест-кейса с TestRail")

        def check_case_id_in_suit():
            if self.__testrail.case.information['suite_id'] == self.__suit_id:
                return True
            else:
                raise TestPlanReportException(f"Тест-кейс: {self.__case_id} не найден в Suite: {self.__suit_id}")

        def check_suit_id_in_run():
            if self.__testrail.run.information['suite_id'] == self.__suit_id:
                self.__testrail.suit.select(self.__suit_id)
                return True
            else:
                raise TestPlanReportException(f"Suite: {self.__suit_id} не найден в Run: {self.__testrail.run.id}")

        def check_run_name_in_plan():
            plan_name = testplan_name_create(suit_name=self.__testrail.suit.get(self.__suit_id)['name'], firmware_version=self.__firmware_version)
            run_name = run_name_create(dev_id=self.__dev_id, dev_serial=self.__dev_serial)
            if not plan_name or not run_name:
                raise TestPlanReportException(f'Run: {run_name}, не найден в Plan: {plan_name}')
            run_id = self.__testrail.get_run_id_by_plan_and_run_names(plan_name=plan_name,
                                                                      run_name=run_name)
            self.__testrail.run.select(run_id)
            return True

        if self.__testrail:
            check_type_case_id()
            check_run_name_in_plan()
            check_suit_id_in_run()
            check_case_id_in_suit()
            return True
        else:
            raise TestPlanReportException('Не удалось отправить результаты на TestRail')

    def write_results(self,
                      status: str,
                      elapsed: float,
                      downtime: float,
                      dev_wait_time: float,
                      settings_load_time: float,
                      comment: str,
                      base_state_time: str,
                      ):

        self.__status = status
        custom_fields = {
            'custom_downtime': seconds_to_timespan(downtime),
            'custom_dev_wait': seconds_to_timespan(dev_wait_time),
            'custom_settings_loading_time': seconds_to_timespan(settings_load_time),
            'custom_base_state_time': seconds_to_timespan(base_state_time),
        }
        elapsed = seconds_to_timespan(elapsed)

        # Получаем результаты теста с TestRail
        if self._check_testrail():
            test_results = self.__testrail.run.get_results_for_case(self.__case_id)
            if self.__status != 'Failed':
                # Проверяем наличие предыдущих результатов на TestRail для этого теста
                if len(test_results) != 0:
                    # Если предыдущий результат не Passed - то считаем что это Retest
                    if test_results[0]['status_id'] != self.__testrail.testcase_statuses['Passed']:
                        self.__status = 'Retest'
            # Проверяем необходимые компоненты для отправки результатов на TestRail и отправляем результаты
            self._send_result_to_testrail(status=self.__status, elapsed=elapsed, comment=comment, custom_fields=custom_fields)

    def _send_result_to_testrail(self, status:str, elapsed:str, comment:str, custom_fields: dict):
        """Отправка результатов на TestRail"""

        if self.__testrail.run.information['is_completed']:
            raise TestPlanReportException(f"Run ID {self.__testrail.run.id} - закрыт")

        if status in self.__testrail.testcase_statuses:
            status = self.__testrail.testcase_statuses[status]
        else:
            raise TestPlanReportException(f'Неизвестный статус теста: {self.__status}')

        self.__testrail.run.add_result_for_case(case_id=self.__case_id,
                                                status_id=status,
                                                comment=comment,
                                                elapsed=elapsed,
                                                custom_fields=custom_fields)
        return True


class TestPlanReportException(Exception):
    pass