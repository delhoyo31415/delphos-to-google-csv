#!/usr/bin/env python3

# Create csv files accepted by Google Suite given Delphos csv files
# Copyright (C) 2021 Pablo del Hoyo Abad <pablodelhoyo1314@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import csv
import secrets
import argparse
import os
import sys
import re

from dataclasses import dataclass, field
from typing import (
    Dict,
    List,
    Tuple,
    Set,
    Optional,
    Any
)
INVALID_CHARACTERS = "áéíóúñÁÉÍÓÚÑ"
REPLACEMENT_CHARACTERS = "aeiounAEIOUN"

EXPECTED_COLS_STUDENT = 3

FIRSTNAME = "First Name [Required]"
LASTNAME = "Last Name [Required]"
EMAIL = "Email Address [Required]"
ORG_UNIT_PATH = "Org Unit Path [Required]"
PASSWORD = "Password [Required]"
CHANGE_PASSWORD = "Change Password at Next Sign-In"

RESET = "\u001b[0m"
BRIGHT_YELLOW = "\u001b[33;1m"
BRIGHT_GREEN = "\u001b[32;1m"
BRIGHT_RED = "\u001b[31;1m"
BRIGHT_CYAN = "\u001b[36;1m"
BRIGHT_BLUE = "\u001b[34;1m"

def with_color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"

class IncorrectCsvValueError(Exception):
    pass

class NaiveLogger:

    _ansi_esc_code_regex = re.compile(r"\\x[a-z0-9]+\[\d+;?\d*m")

    def __init__(self):
        self.messages: List[str] = []

    def show_error(self, msg: str) -> None:
        self.__add_and_show(with_color(f"[ERROR] {msg}", BRIGHT_RED))

    def show_info(self, msg: str) -> None:
        self.__add_and_show(msg)

    def show_warning(self, msg: str) -> None:
        self.__add_and_show(f"{with_color('[AVISO]', BRIGHT_YELLOW)} {msg}")

    def __add_and_show(self, msg) -> None:
        print(msg)
        raw = repr(msg)
        self.messages.append(raw[1:-1] + "\n")

    def write_log_file(self, filename):
        without_esc_codes_msgs = [self._ansi_esc_code_regex.sub("", msg) for msg in self.messages]
        with open(filename, "w") as file:
            file.writelines(without_esc_codes_msgs)

logger = NaiveLogger()

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="delphos_google_converter",
        description="Convierte csv generado por Delphos al csv que admite Google Suite"
    )

    parser.add_argument("csv_google", metavar="csv-google", help="Nombre del archivo csv de Google Suite")
    parser.add_argument("domain", metavar="dominio", help="Dominio del instituto (ej iesinsti.com)")
    parser.add_argument("year", metavar="año", help="Año del curso académico (ej 2021-2022)")
    parser.add_argument("--registro", "-r", metavar="nombre-archivo-registro", action="store", dest="log_filename",
                        help="Nombre del archivo txt con toda la información"
                                " mostrada en la terminal")


    subparser = parser.add_subparsers(dest="action")

    teachers_parser = subparser.add_parser("generar-profesores")
    teachers_parser.add_argument("teacher_csv_file", metavar="csv-profesores",
                        help="Nombre del archivo csv de profesores generado por Delphos")
    teachers_parser.add_argument("--salida", "-s", metavar="nombre-salida", dest="output", action="store",
                        default="profes_nuevos.csv",
                        help="Nombre de salida del archivo csv con los"
                            "nuevos profesores (defecto profes_nuevos.csv)")

    students_parser = subparser.add_parser("generar-alumnos")
    students_parser.add_argument("--directorio", "-d", dest="students_directory", action="store", default="alumnos-delphos",
                        help="Directorio donde se encuentran todos los csvs descargados de Delphos")
    group = students_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--archivo", "-a", dest="course_unit_csv", action="store",
                        help="Archivo csv que contiene el curso y la ruta de la organización")
    group.add_argument("--manual", "-m", nargs=2, action="store",
                        help="Curso (clase) y ruta de la organización sin incluir /")
    students_parser.add_argument("--salida", "-s", metavar="nombre-salida", dest="output", action="store",
                        default="alumnos-nuevos",
                        help="Nombre de salida de la carpeta donde se guardan todos los csvs de los nuevos alumnos")

    return parser.parse_args()

def random_number_only_password(digits) -> str:
    password = str(1 + secrets.randbelow(9))
    password += "".join([str(secrets.randbelow(10)) for _ in range(digits - 1)])
    return password

def remove_accent(letter) -> str:
    if letter in INVALID_CHARACTERS:
        return REPLACEMENT_CHARACTERS[INVALID_CHARACTERS.index(letter)]
    return letter

def remove_all_accents(word) -> str:
    return "".join(remove_accent(letter) for letter in word)

@dataclass(frozen=True)
class SchoolContext:
    domain: str = ""
    org_path_unit: str = "/"
    current_year: str = ""

    fieldnames: Optional[List[str]] = field(default=None, repr=False)
    all_names: Optional[Set[str]] = field(default=None, repr=False)
    all_emails: Optional[Set[str]] = field(default=None, repr=False)

class SchoolPerson:

    # also matches usernames of the form juan.perez@iesuninstituo.es
    _email_regex = re.compile(r"([A-Za-z\.]+)(\d*)@")

    def __init__(self, firstname: str, lastname: str):
        self.firstname = firstname
        self.lastname = lastname
        self.password = random_number_only_password(8)
        
        self.email: str = ""
        self.org_path_unit = ""

    def as_csv_dict(self) -> Dict[str, str]:
        return {
            FIRSTNAME: self.firstname,
            LASTNAME: self.lastname,
            EMAIL: self.email,
            PASSWORD: self.password,
            ORG_UNIT_PATH: self.org_path_unit,
            CHANGE_PASSWORD: "TRUE"
        }

    @property
    def fullname(self) -> str:
        return f"{self.firstname} {self.lastname.strip()}"

    def update_email_user(self) -> None:
        self.email = self._email_regex.sub(self._new_user_name_email, self.email)

    def build_email(self, domain: str) -> None:
        raise NotImplementedError("Método implementado en clases descendientes")

    @classmethod
    def from_csv(cls, csv_data: Any) -> SchoolPerson:
        raise NotImplementedError("Método implementado en clases descendientes")

    def _new_user_name_email(self, match: re.Match) -> str:
        if not match:
            raise ValueError("Formato de email no ha podido ser reconocido")
        return ""

    def __str__(self) -> str:
        return f"{self.firstname} {self.lastname} ({self.email})"

class Teacher(SchoolPerson):
    
    def __init__(self, firstname: str, lastname: str):
        super().__init__(firstname, lastname)

    def build_email(self, domain: str) -> None:
        first_surname = self.lastname.split()[0]
        username = remove_all_accents(self.firstname[0].lower() + first_surname.lower())
        self.email = f"{username}@{domain}"

    @classmethod
    def from_csv(cls, csv_data: str) -> Teacher:
        name_list = csv_data[0].split(", ")
        if len(name_list) != 2:
            raise IncorrectCsvValueError("Nombre formato incorrecto", csv_data[0])
        lastname, firstname = name_list
        return cls(firstname.strip(), lastname.strip())

    def _new_user_name_email(self, match: re.Match) -> str:
        super()._new_user_name_email(match)

        main_user_name, last_nums = match.groups()

        if last_nums:
            f"{main_user_name}{int(last_nums) + 1}@"
        return f"{main_user_name}2@"

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email})")

class Student(SchoolPerson):

    def __init__(self, firstname: str, lastname: str, course: str, enrollment_id: str):
        super().__init__(firstname, lastname)
        self.enrollment_id = enrollment_id
        self.enrollment_year = enrollment_id.split("/")[0]
        self.course = course

    def build_email(self, domain) -> str:
        first_surname = self.lastname.split()[0]
        user_name = remove_all_accents(self.firstname[0].lower() + first_surname.lower())
        # add the two last digit of the enrollment id. I did not choose this criteria to create emails. Someone
        # before me did it.
        user_name += self.enrollment_id[-2:]
        self.email = f"{user_name}@{domain}"

    def _new_user_name_email(self, match: re.Match) -> str:
        super()._new_user_name_email(match)

        # these rules were imposed to me
        main_user_name, last_nums = match.groups()
        next_nums = int(last_nums) + 1
        if next_nums < 10:
            next_nums = f"0{next_nums}"
        return f"{main_user_name}{next_nums}@"

    @classmethod
    def from_csv(cls, csv_data: List[str]) -> Student:
        if len(csv_data) < EXPECTED_COLS_STUDENT:
            raise IncorrectCsvValueError("Número de columnas incorrecto", len(csv_data))

        name_list = csv_data[0].split(", ")
        if len(name_list) != 2:
            raise IncorrectCsvValueError("Nombre formato incorrecto", csv_data[0])
        lastname, firstname = name_list

        divide_course_list = csv_data[1].split("º ")
        if len(divide_course_list) != 2:
            raise IncorrectCsvValueError("Curso formato incorrecto", csv_data[1])
        course = "-".join(divide_course_list)

        enrollment_id = csv_data[2]

        # strip just in case
        return cls(firstname.strip(), lastname.strip(), course.strip(), enrollment_id.strip())

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email}, course={self.course}, "
                f"enrollment_id={self.enrollment_id})")

def change_email_if_needed(person: SchoolPerson, all_emails: Set[str]) -> None:
    while person.email in all_emails:
        old_email = person.email
        person.update_email_user()
        logger.show_warning(f"{old_email} ya existe. Cambiándolo a {person.email}")

    all_emails.add(person.email)

def write_teachers_csv(context: SchoolContext, teachers: List[Teacher], csv_filename: str) -> None:
    with open(csv_filename, "w") as csv_file:
        csv_writer = csv.DictWriter(csv_file, context.fieldnames)
        csv_writer.writeheader()
        for teacher in teachers:
            if teacher.fullname not in context.all_names:
                teacher.org_path_unit = context.org_path_unit + "Profesores"
                teacher.build_email(context.domain)
                change_email_if_needed(teacher, context.all_emails)
                logger.show_info(f"Creando {with_color(teacher.fullname + ' (' + teacher.email + ')', BRIGHT_BLUE)} "
                                    f"en {with_color(teacher.org_path_unit, BRIGHT_CYAN)}")

                csv_writer.writerow(teacher.as_csv_dict())

def write_student_course_csv(context: SchoolContext, course_students: List[Student], org_path: str, filename: str) -> None:
    non_existant_students = [student for student in course_students if student.fullname not in context.all_names]

    if non_existant_students:
        with open(filename, "w") as csv_file:
            csv_writer = csv.DictWriter(csv_file, context.fieldnames)
            csv_writer.writeheader()
            for student in non_existant_students:
                student.build_email(context.domain)
                student.org_path_unit = context.org_path_unit + org_path

                change_email_if_needed(student, context.all_emails)
                text = f"Creando {with_color(student, BRIGHT_BLUE)} en {with_color(student.org_path_unit, BRIGHT_CYAN)}"
                if student.enrollment_year == context.current_year:
                    text = with_color("[NUEVA MATRÍCULA] ", BRIGHT_GREEN) + text
                else:
                    text = with_color("[CASO EXTRAÑO] ", BRIGHT_YELLOW) + text
                logger.show_info(text)
                csv_writer.writerow(student.as_csv_dict())
    elif course_students:
        logger.show_warning(f"No hay ningún alumno nuevo de {course_students[0].course}")
    else:
        logger.show_error("La lista 'course_students' no tiene ningún estudiante")

def get_student_csv_filenames(directory: str) -> List[str]:
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".csv")]

def load_students(csv_filenames: List[str]) -> Dict[str, Student]:
    course_to_student = {}

    for csv_filename in csv_filenames:
        with open(csv_filename, encoding="latin_1") as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)
            for row in csv_reader:
                try:
                    student = Student.from_csv(row)
                except IncorrectCsvValueError as exc:
                    logger.show_error(f"Valor en csv de estudiante no permitido: {exc.args}")
                    sys.exit(1)
                if student.course not in course_to_student:
                    course_to_student[student.course] = []
                course_to_student[student.course].append(student)

    return course_to_student

def load_course_unit_path(csv_filename: str) -> List[Tuple[str, str]]:
    with open(csv_filename) as csv_file:
        csv_reader = csv.reader(csv_file)
        return [(row[1], row[0]) for row in csv_reader]

def load_teachers(csv_filename: str) -> List[Teacher]:
    with open(csv_filename, encoding="latin_1") as csv_file:
        csv_reader = csv.reader(csv_file)
        # ignore first row
        next(csv_reader)
        try:
            return [Teacher.from_csv(data) for data in csv_reader]
        except IncorrectCsvValueError as exc:
            logger.show_error(f"Valor en csv de estudiante no permitido: {exc.args}")
            sys.exit(1)

def get_google_csv_data(filename: str) -> Tuple[str, Set[str], Set[str]]:
    with open(filename) as csv_filename:
        csv_reader = csv.reader(csv_filename)
        all_names = set()
        all_emails = set()

        fieldnames = next(csv_reader)

        for row in csv_reader:
            name = f"{row[0].strip()} {row[1].strip()}"
            all_names.add(name)
            all_emails.add(row[2])

    return fieldnames, all_names, all_emails

def create_context(args: argparse.Namespace, google_data: Tuple[Set[str], Set[str]]) -> SchoolContext:
    domain = args.domain
    org_unit_path = f"/Curso {args.year}/"
    current_year = re.match(r"(\d+)[-/\s]\d+", args.year).group(1)

    fieldnames, all_names, all_emails = google_data

    return SchoolContext(domain, org_unit_path,
                        current_year, fieldnames, all_names, all_emails)

def main():
    args = get_args()
    context = create_context(args, get_google_csv_data(args.csv_google))

    if args.action == "generar-profesores":
        all_teachers = load_teachers(args.teacher_csv_file)
        write_teachers_csv(context, all_teachers, args.output)
    elif args.action == "generar-alumnos":
        files_path = get_student_csv_filenames(args.students_directory)
        course_to_students = load_students(files_path)

        if not os.path.isdir(args.output):
            os.mkdir(args.output)

        if args.course_unit_csv:
            course_unit_paths = load_course_unit_path(args.course_unit_csv)

            for course, unit_path in course_unit_paths:
                filename = os.path.join(args.output, course + ".csv")
                if course in course_to_students:
                    write_student_course_csv(context, course_to_students[course], unit_path, filename)
                else:
                    logger.show_warning(f"No se ha encontrado el curso {course}")
        else:
            course, unit_path = args.manual
            filename = os.path.join(args.output, course + ".csv")
            if course in course_to_students:
                write_student_course_csv(context, course_to_students[course], unit_path, filename)
            else:
                logger.show_warning(f"No se ha encontrado el curso {course}")

    if args.log_filename:
        logger.write_log_file(args.log_filename)

if __name__ == "__main__":
    main()