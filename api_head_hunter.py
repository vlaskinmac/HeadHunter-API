import argparse
import logging
import os

import requests
from requests import HTTPError
from dotenv import load_dotenv
from itertools import count
from terminaltables import AsciiTable


def predict_salary_avg(salary_from, salary_to):
    if salary_from or salary_to:
        if not salary_from:
            expected_salary = salary_to * 0.8
        elif not salary_to:
            expected_salary = salary_from * 1.2
        else:
            expected_salary = (salary_to + salary_from) / 2
        return expected_salary
    else:
        return None


def predict_rub_salary_hh(recruitment_of_vacancies, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    city = 1
    vacancy_grouped = []
    for vacancy in recruitment_of_vacancies:
        grouped_vacancies = {}
        salary_group = []
        vacancy_result = 0

        url = "https://api.hh.ru/vacancies"
        param = {
            "text": vacancy,
            "area": city,
            "period": period,
            "page": vacancy_result,
        }
        for page in count():
            vacancy_result += 1
            response = requests.get(url, params=param, headers=headers)
            response.raise_for_status()
            logging.warning(response.status_code)
            response_set = response.json()
            if page > response_set["pages"]:
                break
            for salary in response_set["items"]:
                if salary["salary"]:
                    if salary["salary"]["currency"] == "RUR":
                        expected_salary = predict_salary_avg(salary["salary"]["from"], salary["salary"]["to"])
                        if expected_salary:
                            salary_group.append(expected_salary)
                    city_search = salary["area"]["name"]

        salary_avg = int(sum(salary_group)) / len(salary_group)
        grouped_vacancies[f"{vacancy}"] = {
            "vacancies_found": response_set["found"],
            "vacancies_processed": len(salary_group),
            "salary_avg": int(salary_avg),
            "city": city_search
        }
        vacancy_grouped.append(grouped_vacancies)
    return vacancy_grouped


def predict_rub_salary_sj(recruitment_of_vacancies, token, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": token,
    }
    vacancy_grouped = []
    for vacancy in recruitment_of_vacancies:
        grouped_vacancies = {}
        salary_group = []
        page = 0
        url = "https://api.superjob.ru/2.0/vacancies"
        param = {
            "period": period,
            "town": "Москва",
            "keywords": vacancy,
            "currency": "rub",
            "count": 20,
            "page": page,
        }
        for page in count():
            page += 1
            response = requests.get(url, params=param, headers=headers)
            response.raise_for_status()
            logging.warning(response.status_code)
            collecting_sj = response.json()
            if collecting_sj['more']:
                if page > collecting_sj["total"]:
                    break
            else:
                if page > collecting_sj["total"]:
                    break
            for salary in collecting_sj["objects"]:
                expected_salary = predict_salary_avg(salary["payment_from"], salary["payment_to"])
                if expected_salary:
                    salary_group.append(expected_salary)
            city_search = salary["town"]["title"]

        salary_avg = int(sum(salary_group)) / len(salary_group)
        grouped_vacancies[f"{vacancy}"] = {
            "vacancies_found": collecting_sj["total"],
            "vacancies_processed": len(salary_group),
            "salary_avg": int(salary_avg),
            "city": city_search
        }
        vacancy_grouped.append(grouped_vacancies)
    return vacancy_grouped


def statistic_for_table_hh(recruitment_of_vacancies, period):
    recruitment_of_vacancies_hh = predict_rub_salary_hh(recruitment_of_vacancies, period)
    for final_language in recruitment_of_vacancies_hh:
        for statistic in final_language:
            hh_table = [
                ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
            ]
            title_hh = f"HeadHunter - {final_language[statistic]['city']}"
            for final_language in recruitment_of_vacancies_hh:
                for statistic in final_language:
                    hh_table.append(
                        [
                            statistic, final_language[statistic]['vacancies_found'],
                            final_language[statistic]["vacancies_processed"],
                            final_language[statistic]["salary_avg"],
                        ]
                    )

    return hh_table, title_hh


def statistic_for_table_sj(recruitment_of_vacancies, token, period):
    recruitment_of_vacancies_sj = predict_rub_salary_sj(recruitment_of_vacancies, token, period)
    for final_language in recruitment_of_vacancies_sj:
        for statistic in final_language:
            sj_table = [
                ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
            ]
            title_sj = f"SuperJob - {final_language[statistic]['city']}"
            for final_language in recruitment_of_vacancies_sj:
                for statistic in final_language:
                    sj_table.append(
                        [
                            statistic, final_language[statistic]['vacancies_found'],
                            final_language[statistic]["vacancies_processed"],
                            final_language[statistic]["salary_avg"],
                        ]
                    )
    return sj_table, title_sj


def get_vacancy_from_user():
    parser = argparse.ArgumentParser(
        description="The Code collects salary figures for vacancies from two sources: HeadHunter, SuperJob."
    )
    recruitment_of_vacancies = ["python", "javascript", "golang", "java", "c++", "typescript", "c#"]
    parser.add_argument(
        "-v", "--vacancy", nargs="+", default=recruitment_of_vacancies,
        help="Set the vacancies use arguments: '-v or --vacancy'"
    )
    parser.add_argument(
        "-p", "--period", nargs="+", default=30, help="Set the period use arguments: '-p or --period'"
    )
    args = parser.parse_args()
    args_vacancy = args.vacancy
    args_period = args.period
    return args_vacancy, args_period


def build_table(hh_table, title_hh):
    table_instance = AsciiTable(hh_table, title_hh)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    return table_instance.table


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        filename="logs.log",
        filemode="w",
        format="%(asctime)s - [%(levelname)s] - %(funcName)s() - [line %(lineno)d] - %(message)s",
    )
    load_dotenv()
    token = os.getenv("API_KEY_SUPERJOB")
    recruitment_of_vacancies, period = get_vacancy_from_user()
    try:
        hh_table, title_hh = statistic_for_table_hh(recruitment_of_vacancies, period)
        print(build_table(hh_table, title_hh))

        sj_table, title_sj = statistic_for_table_sj(recruitment_of_vacancies, token, period)
        print(build_table(sj_table, title_sj))
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)
        raise exc
