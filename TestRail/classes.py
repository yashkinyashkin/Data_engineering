import abc
from TestRailAPI import APIError

from TestRailAPI import APIClient


def _check_none(value_1, value_2):
    if value_1 is not None:
        return value_1
    elif value_2 is not None:
        return value_2
    else:
        raise Exception("'None' во входных параметрах")


class PatternTestRail(abc.ABC):
    _keyword = None

    def __init__(self,
                 client: APIClient,
                 project_id: int,
                 object_id: int = None):
        self.__client = client
        self.__project_id = project_id
        self.__id = None
        self.__full_info = None
        self.__keyword = self._keyword
        if object_id:
            self.select(object_id)

    @property
    def client(self):
        return self.__client

    @property
    def keyword(self):
        return self.__keyword

    @property
    def information(self):
        return self.__full_info

    @property
    def id(self):
        return self.__id

    @property
    def project_id(self):
        return self.__project_id

    def check(self, object_id) -> bool:
        try:
            self.get(object_id)
            return True
        except APIError as testrail_error:
            return False
        except Exception as error:
            raise error

    def select(self, object_id) -> dict:
        if self.check(object_id):
            self.__full_info = self.get(object_id)
            self.__id = self.__full_info['id']
            return self.__full_info

    def add(self, *args, **kwargs) -> dict:
        information = self.__client.send_post(f'add_{self.__keyword}/{self.__project_id}', *args, **kwargs)
        self.select(information['id'])
        return information

    def get(self, object_id=None) -> dict:
        object_id = _check_none(object_id, self.__id)
        return self.__client.send_get(uri=f'get_{self.__keyword}/{object_id}')

    def get_all(self) -> list:
        return self.__client.send_get(uri=f'get_{self.__keyword}s/{self.__project_id}')

    def delete(self, object_id=None) -> dict:
        object_id = _check_none(object_id, self.__id)
        return self.__client.send_post(uri=f'delete_{self.__keyword}/{object_id}', data='')

    def close(self, object_id=None) -> dict:
        object_id = _check_none(object_id, self.__id)
        return self.__client.send_post(uri=f'close_{self.__keyword}/{object_id}', data='')

    def get_ids_by_name(self, object_name: str) -> list:
        all_objects = self.get_all()
        objects_list = []
        for obj in all_objects:
            if object_name == obj['name']:
                objects_list.append(obj['id'])
        return objects_list
    
    def update(self, object_id=None, data:dict='') -> dict:
        object_id = _check_none(object_id, self.__id)
        return self.__client.send_post(uri=f'update_{self.__keyword}/{object_id}', data = data)
    
    def __str__(self) -> str:
        return f"Type: {self.__keyword}  ID: {self.__id}, Project ID: {self.__project_id}"

    def __getitem__(self, prop):
        for item in self.__full_info:
            if item == prop:
                return self.__full_info[prop]

        return None

    def __contains__(self, prop):
        for item in self.__full_info:
            if item == prop:
                return True
        return False


class Case(PatternTestRail):
    _keyword = 'case'

    def get_all(self) -> dict:
        pass

    def add(self,
            section_id: int = None,
            title: str = None,
            template_id: int = None,
            type_id: int = None,
            priority_id: int = None,
            estimate: int = None,
            milestone_id: int = None,
            refs: int = None,
            custom_data: dict = None
            ) -> dict:
        data = {
            'section_id': section_id,
            'title': title,
            'template_id': template_id,
            'type_id': type_id,
            'priority_id': priority_id,
            'estimate': estimate,
            'milestone_id': milestone_id,
            'refs': refs,
            'custom_data': custom_data,
        }
        return super().add(data)

    def close(self, object_id=None) -> None:
        return None


class Plan(PatternTestRail):
    _keyword = 'plan'

    def __init__(self, client: APIClient, project_id: int, plan_id: int = None):
        self.run = Run(client, project_id)
        super().__init__(client, project_id, plan_id)
        self.run.plan_id = self.id

    def select(self, object_id) -> dict:
        result = super().select(object_id)
        self.run.plan_id = self.id
        return result

    def add(self,
            name: str,
            description: str = None,
            milestone_id: int = None,
            entries: list = None) -> dict:
        """
        Creates a new test plan and assigns it to self

        :param name:                    The name of the test plan
        :param description:             The description of the test plan
        :param milestone_id:            The ID of the milestone to link to the test plan
        :param entries:                 An array of objects describing the test runs of the plan, see the example below and add_plan_entry

        :return:                        Return information about Test Plan

        """
        data = {
            'name': name,
            'description': description,
            'milestone_id': milestone_id,
            'entries': entries,
        }
        return super().add(data)

    def add_entry_run(self,
                      suite_id: int,
                      name: str = None,
                      description: str = None,
                      assignedto_id: int = None,
                      include_all: bool = True,
                      case_ids: list = None,
                      config_ids: list = None,
                      refs: str = None,
                      runs: list = None,
                      plan_id: int = None) -> dict:
        """
        Adds one or more new test runs to a test plan.

        :param suite_id:            The ID of the test suite for the test run(s)
        :param name:                The name of the test run(s)
        :param description:         The description of the test plan
        :param assignedto_id:       1 to return completed test plans only. 0 to return active test plans only
        :param include_all:         Limit the result to :limit test plans. Use :offset to skip records
        :param case_ids:            An array of case IDs for the custom case selection (Required if include_all is false)
        :param config_ids:          An array of configuration IDs used for the test run of the test plan entry
        :param refs:                A comma-separated list of references/requirements
        :param runs:                An array of test runs
        :param plan_id:             The ID of the plan the test runs should be added to
                                    If plan_id is None - will be used self plan_id(if exists)

        :return:                    Return information about new test Run
        """
        data = {
            'suite_id': suite_id,
            'name': name,
            'description': description,
            'assignedto_id': assignedto_id,
            'include_all': include_all,
            'case_ids': case_ids,
            'config_ids': config_ids,
            'refs': refs,
            'runs': runs,
        }

        plan_id = _check_none(plan_id, self.id)
        run_information = self.client.send_post(f'add_plan_entry/{plan_id}', data)['runs'][0]

        return run_information

    def runs_get(self, plan_id: int = None) -> list:
        """
        :param plan_id:             The ID of the test plan
                                    If plan_id is None - will be used self plan_id(if exists)

        :return:                    Return all Runs in Test Plan
        """
        plan_id = _check_none(plan_id, self.id)
        entries_list = self.get(plan_id)['entries']
        runs_list = []
        for entry in entries_list:
            for run in entry['runs']:
                runs_list.append(run)
        return runs_list

    def get_runs_ids_by_run_name(self, run_name: str, plan_id: int = None) -> list:
        """
        :param plan_id:             The ID of the test plan
                                    If plan_id is None - will be used self plan_id(if exists)
        :param run_name:            Run's name to find

        :return:                    Return a list of run IDs with the name of the incoming run
        """
        plan_id = _check_none(plan_id, self.id)
        runs = self.runs_get(plan_id)
        runs_list = []
        for run in runs:
            if run_name == run['name']:
                runs_list.append(run['id'])
        return runs_list

    def update_plan_entry(self,
                          entry_id,
                          name: str = None,
                          description: str = None,
                          assignedto_id: int = None,
                          include_all: bool = None,
                          case_ids: list = None,
                          plan_id: int = None):

        plan_id = _check_none(plan_id, self.id)
        data = {
            'name': name,
            'description': description,
            'assignedto_id': assignedto_id,
            'include_all': include_all,
            'case_ids': case_ids
        }
        return self.client.send_post(f'update_plan_entry/{plan_id}/{entry_id}', data)


class Run(PatternTestRail):
    _keyword = 'run'
    plan_id = None

    def add(self,
            suite_id: int,
            name: str,
            description: str = None,
            milestone_id: int = None,
            assignedto_id: int = None,
            include_all: bool = True,
            case_ids: list = None,
            refs: str = None
            ) -> dict:
        """
        Creates a new test run.

        :param suite_id:        The ID of the test suite for the test run (optional if the project is operating in single suite mode, required otherwise)
        :param name:            The name of the test run
        :param description:     The description of the test run
        :param milestone_id:    The ID of the milestone to link to the test run
        :param assignedto_id:   1 to return completed test runs only. 0 to return active test runs onlyThe ID of the user the test run should be assigned to
        :param include_all:     True for including all test cases of the test suite and false for a custom case selection (default: true)
        :param case_ids:        An array of case IDs for the custom case selection
        :param refs:            A comma-separated list of references/requirements — requires TestRail 6.1 or later
        :param project_id:      The ID of the project the test run should be added to
                                If project_id is None - will be used self project_id(if exists)

        :return:                Return information about new test Run
        """
        data = {
            'suite_id': suite_id,
            'name': name,
            'description': description,
            'milestone_id': milestone_id,
            'assignedto_id': assignedto_id,
            'include_all': include_all,
            'case_ids': case_ids,
            'refs': refs,
        }
        return super().add(data)

    def get_all(self, plan_id=None):
        plan_id = _check_none(plan_id, self.plan_id)
        just_runs = []
        if plan_id:
            testrail_plan = Plan(self.client, self.project_id, self.plan_id)
            just_runs = testrail_plan.runs_get()

        else:
            testrail_plan = Plan(self.client, self.project_id)
            plans = testrail_plan.get_all()
            for plan in plans:
                just_runs = testrail_plan.runs_get(plan['id'])
            just_runs += super().get_all()

        return just_runs

    def get_results_for_case(self, case_id: int, run_id: int = None) -> dict:
        """
        :param case_id:	        The ID of the test case
        :param run_id:          The ID of the test run

        :return:                Returns a list of test results for a test run and case combination.
        """
        run_id = _check_none(run_id, self.id)

        return self.client.send_get(uri=f'get_results_for_case/{run_id}/{case_id}')

    def get_results_for_run(self, run_id: int = None) -> list:
        """
        :param run_id:          The ID of the test run

        :return:                Returns a list of test results for a test run.
        """
        run_id = _check_none(run_id, self.id)
        return self.client.send_get(uri=f'get_results_for_run/{run_id}')

    def add_result_for_case(self,
                            case_id: int,
                            status_id: int,
                            comment: str = None,
                            version: str = None,
                            elapsed=None,
                            defects: str = None,
                            assignedto_id: int = None,
                            run_id: int = None,
                            custom_fields: dict = None) -> dict:
        """
        Adds a new test result, comment or assigns a test (for a test run and case combination)

        :param case_id:	            The ID of the test case

        :param status_id:           The ID of the test status. The default system statuses have the following IDs:
                                        1: Passed
                                        2: Blocked
                                        3: Untested (not allowed when adding a new result)
                                        4: Retest
                                        5: Failed
                                        You can get a full list of system and custom statuses via get_statuses.
                                        (https://support.testrail.com/hc/en-us/articles/7077935129364-Statuses#getstatuses)
        :param comment:             The comment/description for the test result
        :param version:             The version or build you tested against
        :param elapsed:             The time it took to execute the test, e.g. “30s” or “1m 45s”
        :param defects:             A comma-separated list of defects to link to the test result
        :param assignedto_id:       The ID of a user the test should be assigned to
        :param run_id:              The ID of the test run
        :param custom_fields        Custom fields from your TestRail
                                    Example:
                                    {
                                     'custom_example_field': value,
                                     'custom_example_field_1': value_1
                                    }
                                    Prefix 'custom_' is required

        :return:                    Return full information about case
        """
        data = {
            'status_id': status_id,
            'comment': comment,
            'version': version,
            'elapsed': elapsed,
            'defects': defects,
            'assignedto_id': assignedto_id,
        }
        if custom_fields is not None:
            data = {**data, **custom_fields}
        run_id = _check_none(run_id, self.id)
        return self.client.send_post(uri=f'add_result_for_case/{run_id}/{case_id}', data=data)

    def add_results_for_cases(self, testcases_results_list: list, run_id: int = None) -> list:
        """
        Adds one or more new test results,
        comments or assigns one or more tests (using the case IDs).

        Please note that all referenced tests must belong to the same test run.

        :param run_id:                      The ID of the test run
        :param testcases_results_list:      Array of testcases results as in add_result_for_case() function
                                            Example:
                                            [
                                                    {
                                                        "case_id": 1,
                                                        "status_id": 5,
                                                        "comment": "This test failed",
                                                        "defects": "TR-7"
                                                    },
                                                    {
                                                        "case_id": 2,
                                                        "status_id": 1,
                                                        "comment": "This test passed",
                                                        "elapsed": "5m",
                                                        "version": "1.0 RC1"
                                                    },
                                                    {
                                                        "case_id": 1,
                                                        "assignedto_id": 5,
                                                        "comment": "Assigned this test to Joe"
                                                    }
                                            ]

        :return:                            Return full information about cases
        """
        data = {
            'results': testcases_results_list
        }
        run_id = _check_none(run_id, self.id)
        return self.client.send_post(uri=f'add_results_for_cases/{run_id}', data=data)

    def get_tests(self, run_id: int = None):
        run_id = _check_none(run_id, self.id)
        return self.client.send_get(uri=f'get_tests/{run_id}')


class Milestones(PatternTestRail):
    _keyword = 'milestone'

    def add(self,
            name: str,
            description: str = None,
            due_on: str = None,
            parent_id: int = None,
            refs: str = None,
            start_on: str = None,
            ) -> dict:
        """
        Creates a new milestone.
        :param name:                    The name of the milestone
        :param description:             The description of the milestone
        :param due_on:                  The due date of the milestone (as UNIX timestamp)
        :param parent_id:               The ID of the parent milestone, if any (for sub-milestones) — requires TestRail 5.3 or later
        :param refs:                    A comma-separated list of references/requirements — requires TestRail 6.4 or later
        :param start_on:                The scheduled start date of the milestone (as UNIX timestamp) — requires TestRail 5.3 or later

        :param project_id:              The ID of the project the milestone should be added to
                                        If project_id is None - will be used self project_id(if exists)

        :return:                        Return information about new Milestone and select it
        """
        data = {
            'name': name,
            'description': description,
            'due_on': due_on,
            'parent_id': parent_id,
            'refs': refs,
            'start_on': start_on,
        }
        return super().add(data)

    def close(self, object_id=None) -> None:
        return None


class Suite(PatternTestRail):
    _keyword = 'suite'

    def close(self, object_id=None) -> None:
        return None

    def get_cases(self):

        return self.client.send_get(uri=f'get_cases/{self.project_id}&suite_id={self.id}')


class Test(PatternTestRail):
    _keyword = 'test'


class TestRailProject:
    def __init__(self, client: APIClient, project_id: int):
        self.plan = Plan(client, project_id)
        self.run = Run(client, project_id)
        self.suit = Suite(client, project_id)
        self.milestones = Milestones(client, project_id)
        self.case = Case(client, project_id)

        self.testcase_statuses = {
            "Passed": 1,
            "Blocked": 2,
            "Retest": 4,
            "Failed": 5
        }

    def get_run_id_by_plan_and_run_names(self, run_name, plan_name):
        plans_ids = self.plan.get_ids_by_name(plan_name)
        if len(plans_ids) == 1:
            plan_id = plans_ids[0]
        elif len(plans_ids) == 0:
            raise TestRailClassException(f"Не найдено ни одного Plan с названием {plan_name}")
        else:
            raise TestRailClassException(f"Найдено более одного Plan с названием {plan_name}")

        runs_ids = self.plan.get_runs_ids_by_run_name(run_name=run_name, plan_id=plan_id)
        if len(runs_ids) == 1:
            run_id = runs_ids[0]
        elif len(runs_ids) == 0:
            raise TestRailClassException(f"Не найдено ни одного Run с названием {run_name}")
        else:
            raise TestRailClassException(f"Найдено более одного Run с названием {run_name}")

        return run_id


class TestRailClassException(Exception):
    pass
