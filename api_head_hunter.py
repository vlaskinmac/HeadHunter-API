import argparse
import logging
import os

import requests

from dotenv import load_dotenv
from requests import HTTPError
from terminaltables import AsciiTable


def predict_avg_salary(salary_from, salary_to):
    if not salary_from or salary_to:
        if not salary_from:
            expected_salary = salary_to * 0.8
        elif not salary_to:
            expected_salary = salary_from * 1.2
        else:
            expected_salary = (salary_to + salary_from) / 2
        return expected_salary


def predict_rub_salary_hh(vacancy, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    salary_group = []
    page = 1
    url = "https://api.hh.ru/vacancies"
    param = {
        "text": vacancy,
        "period": period,
        "page": page,
    }
    while True:
        response = requests.get(url, params=param, headers=headers)
        response.raise_for_status()
        logging.warning(response.status_code)
        response_set = response.json()
        if page == response_set["pages"]:
            break
        for salary in response_set["items"]:
            if salary["salary"] and salary["salary"]["currency"] == "RUR":
                    expected_salary = predict_avg_salary(salary["salary"]["from"], salary["salary"]["to"])
                    if expected_salary:
                        salary_group.append(expected_salary)
        page += 1
    return response_set["found"], salary_group


def predict_rub_salary_sj(vacancy, token, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": token,
    }
    salary_group = []
    page = 0
    url = "https://api.superjob.ru/2.0/vacancies"
    while True:
        param = {
            "period": period,
            "town": "Москва",
            "keywords": vacancy,
            "currency": "rub",
            "count": 20,
            "page": page,
        }
        response = requests.get(url, params=param, headers=headers)
        response.raise_for_status()
        logging.warning(response.status_code)
        collecting_sj = response.json()
        if collecting_sj['more']:
            if page >= collecting_sj["total"]:
                break
        else:
            if page >= collecting_sj["total"]:
                break
        for salary in collecting_sj["objects"]:
            expected_salary = predict_avg_salary(salary["payment_from"], salary["payment_to"])
            if expected_salary:
                salary_group.append(expected_salary)
        page += 1
        sj_collecting = collecting_sj["total"]
    return sj_collecting, salary_group


def groups_vacancies_sj(set_vacancies, token, period):
    vacancy_grouped = {}
    for vacancy in set_vacancies:
        total_vacansies_sj, salary_group = predict_rub_salary_sj(vacancy, token, period)
        grouped_vacancies = {
            "vacancies_found": total_vacansies_sj,
            "vacancies_processed": len(salary_group),
            "salary_avg": int(int(sum(salary_group)) / len(salary_group)),
        }
        vacancy_grouped[vacancy] = grouped_vacancies
    return vacancy_grouped


def groups_vacancies_hh(set_vacancies, period):
    vacancy_grouped = {}

    for vacancy in set_vacancies:

        total_vacansies_hh, salary_group = predict_rub_salary_hh(vacancy, period)
        grouped_vacancies = {
            "vacancies_found": total_vacansies_hh,
            "vacancies_processed": len(salary_group),
            "salary_avg": int(int(sum(salary_group)) / len(salary_group)),
        }
        vacancy_grouped[vacancy] = grouped_vacancies
    return vacancy_grouped


def get_vacancy_from_user():
    parser = argparse.ArgumentParser(
        description="The Code collects salary figures for vacancies from two sources: HeadHunter, SuperJob."
    )
    set_vacancies = ["python", "javascript", "golang", "java", "c++", "typescript", "c#"]
    parser.add_argument(
        "-v", "--vacancy", nargs="+", default=set_vacancies,
        help="Set the vacancies use arguments: '-v or --vacancy'"
    )
    parser.add_argument(
        "-p", "--period", default=30, help="Set the period use arguments: '-p or --period'"
    )
    args = parser.parse_args()
    args_vacancy = args.vacancy
    args_period = args.period
    return args_vacancy, args_period


def build_table(recruitment_of_vacancies, title):
    table = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    ]
    for language, statistic in recruitment_of_vacancies.items():
        table.append(
            [
                language, statistic['vacancies_found'],
                statistic["vacancies_processed"],
                statistic["salary_avg"],
            ]
        )
    table_instance = AsciiTable(table, title)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    print(table_instance.table)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        filename="logs.log",
        filemode="w",
        format="%(asctime)s - [%(levelname)s] - %(funcName)s() - [line %(lineno)d] - %(message)s",
    )
    load_dotenv()
    token = os.getenv("API_KEY_SUPERJOB")
    set_vacancies, period = get_vacancy_from_user()
    try:
        vacancies_sj = groups_vacancies_sj(set_vacancies, token, period)
        build_table(vacancies_sj, "SuperJob")
        vacancies_hh = groups_vacancies_hh(set_vacancies, period)
        build_table(vacancies_hh, "HeadHunter")
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)


