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
import functools

from dataclasses import dataclass, field
from typing import (
    Dict,
    List,
    Tuple,
    Set,
    Optional,
    Any,
    Callable
)
INVALID_CHARACTERS = "áéíóúñÁÉÍÓÚÑ"
REPLACEMENT_CHARACTERS = "aeiounAEIOUN"
LEAVE_PASSWORD_STR = "****"

EXPECTED_COLS_STUDENT = 3
MINIMUM_ROWS_GOOGLE_CSV = 4
MAXIMUM_COLS_GOOGLE_CSV = 35

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
BRIGHT_MAGENTA = "\u001b[35;1m"

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
    parser.add_argument("-.colocar", "-c", action="store_true", dest="reallocate",
                        help="Si está presente esta opción, entonces se generan archivos csv pensados para "
                        "recolocar a los alumnos que se encuentran en Google Suite")

    subparser = parser.add_subparsers(dest="action")

    teachers_parser = subparser.add_parser("generar-profesores")
    teachers_parser.add_argument("teacher_csv_file", metavar="csv-profesores",
                        help="Nombre del archivo csv de profesores generado por Delphos")
    teachers_parser.add_argument("--salida", "-s", metavar="nombre-salida", dest="output", action="store",
                        default="profes-generados.csv",
                        help="Nombre de salida del archivo csv con los"
                            "profesores (defecto profes-generados.csv)")

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

class SchoolPerson:

    # also matches usernames of the form juan.perez@iesuninstituo.es
    _email_regex = re.compile(r"([A-Za-z\.]+)(\d*)@")

    def __init__(self, firstname: str, lastname: str, email: Optional[str]=None, org_path_unit: Optional[str]=None):
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.org_path_unit = org_path_unit
        self.fullname = f"{self.firstname} {self.lastname}"
        self.is_lost = False
        
        self.password = LEAVE_PASSWORD_STR

    def as_csv_dict(self) -> Dict[str, str]:
        return {
            FIRSTNAME: self.firstname,
            LASTNAME: self.lastname,
            EMAIL: self.email,
            PASSWORD: self.password,
            ORG_UNIT_PATH: self.org_path_unit,
            CHANGE_PASSWORD: "TRUE" if self.password != LEAVE_PASSWORD_STR else ""
        }

    def generate_account_attributes(self, domain: str):
        self.password = random_number_only_password(8)
        self.email = self._build_email(domain)

    def update_email(self) -> None:
        self.email = self._email_regex.sub(self._new_user_name_email, self.email)

    @classmethod
    def from_google_csv(cls, google_csv_data: List[str]) -> SchoolPerson:
        if len(google_csv_data) < MINIMUM_ROWS_GOOGLE_CSV:
            raise IncorrectCsvValueError("Número de columnas en csv de google incorrecto",  {len(google_csv_data)})

        firstname = google_csv_data[0].strip()
        lastname = google_csv_data[1].strip()
        email = google_csv_data[2]
        org_path_unit = google_csv_data[5]

        return cls(firstname, lastname, email, org_path_unit)

    @classmethod
    def from_csv(cls, csv_data: Any) -> SchoolPerson:
        raise NotImplementedError("Método implementado en clases descendientes")

    def _build_email(self, domain: str) -> str:
        raise NotImplementedError("Método implementado en clases descendientes")

    def _new_user_name_email(self, match: re.Match) -> str:
        if not match:
            raise ValueError("Formato de email no ha podido ser reconocido")
        return ""

    def __str__(self) -> str:
        if self.email:
            return f"{self.fullname} ({self.email})"
        return self.fullname

@dataclass
class SchoolContext:
    fieldnames: List[str] = field(repr=False)
    all_google_users: Set[SchoolPerson] = field(default=None, repr=False)

    domain: str = ""
    org_path_unit: str = "/"
    current_year: str = ""

    @functools.cached_property
    def all_emails(self) -> Set[str]:
        return set([user.email for user in self.all_google_users])

    def create_single_reference(self, delphos_users: List[SchoolPerson]):
        """ Create just a single reference for each person """

        same_ref_users = set()
        name_google_users = {user.fullname: user for user in self.all_google_users}
        name_delphos_users = {user.fullname: user for user in delphos_users}

        for google_name in name_google_users:
            google_user = name_google_users[google_name]
            if google_name in name_delphos_users:
                base = name_delphos_users[google_name]
                base.email = google_user.email
                base.org_path_unit = google_user.org_path_unit

                same_ref_users.add(base)
            else:
                google_user.is_lost = True
                same_ref_users.add(google_user)

        self.all_google_users = same_ref_users

class Teacher(SchoolPerson):

    @classmethod
    def from_csv(cls, csv_data: str) -> Teacher:
        name_list = csv_data[0].split(", ")
        if len(name_list) != 2:
            raise IncorrectCsvValueError("Nombre formato incorrecto", csv_data[0])
        lastname, firstname = name_list
        return cls(firstname.strip(), lastname.strip())

    def _build_email(self, domain: str) -> None:
        first_surname = self.lastname.split()[0]
        username = remove_all_accents(self.firstname[0].lower() + first_surname.lower())
        return f"{username}@{domain}"

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

    def __init__(self, firstname: str, lastname: str, email: Optional[str]=None, org_path_unit: Optional[str]=None,
                    course: Optional[str]=None, enrollment_id: Optional[str]=None):
        super().__init__(firstname, lastname, email, org_path_unit)
        self.course = course
        self.enrollment_id = enrollment_id
        self.enrollment_year: Optional[str] = None

        if self.enrollment_id:
            self.enrollment_year = enrollment_id.split("/")[0]

    def _build_email(self, domain) -> str:
        first_surname = self.lastname.split()[0]
        user_name = remove_all_accents(self.firstname[0].lower() + first_surname.lower())
        # add the two last digit of the enrollment id. I did not choose this criteria to create emails. Someone
        # before me did it.
        user_name += self.enrollment_id[-2:]
        return f"{user_name}@{domain}"

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
        return cls(
            firstname.strip(), lastname.strip(), course=course.strip(), enrollment_id=enrollment_id.strip()
        )

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email}, course={self.course}, "
                f"enrollment_id={self.enrollment_id})")

def write_users(users: str, filename: str, fieldnames: List[str]) -> None:
    dicts_to_write = [user.as_csv_dict() for user in users]
    with open(filename, "w") as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(dicts_to_write)

def generate_lost_users(context: SchoolContext, users: List[SchoolPerson], org_path: str) -> List[SchoolPerson]:
    # @param: users is a list containing instances of just one class
    lost_users = []
    if not users:
        return lost_users
    list_cls = users[0].__class__

    for google_user in context.all_google_users:
        if isinstance(google_user, list_cls) and google_user.is_lost:
            old_org_path = google_user.org_path_unit
            google_user.org_path_unit = context.org_path_unit + org_path
            logger.show_info(f"{with_color('[BAJA]', BRIGHT_MAGENTA)} Moviendo {with_color(google_user, BRIGHT_BLUE)}"
            f" de {with_color(old_org_path, BRIGHT_CYAN)} a {with_color(google_user.org_path_unit, BRIGHT_CYAN)}")
            lost_users.append(google_user)
    return lost_users

def change_email_if_needed(person: SchoolPerson, all_emails: Set[str]) -> None:
    while person.email in all_emails:
        old_email = person.email
        person.update_email()
        logger.show_warning(f"{old_email} ya existe. Cambiándolo a {person.email}")

    all_emails.add(person.email)

def generate_reallocated_users(context: SchoolContext, users: List[SchoolPerson], org_path: str,
                                warning_event: Optional[Callable[[SchoolPerson], None]]=None) -> None:
    for user in users:
        if user not in context.all_google_users:
            if warning_event:
                warning_event(user)
        old_path_unit = user.org_path_unit
        user.org_path_unit = context.org_path_unit + org_path

        if old_path_unit and old_path_unit != user.org_path_unit:
            logger.show_info(f"Recolocando {with_color(user, BRIGHT_BLUE)} de {with_color(old_path_unit, BRIGHT_CYAN)} a "
                            f"{with_color(user.org_path_unit, BRIGHT_CYAN)}")
        elif old_path_unit == user.org_path_unit:
            logger.show_info(f"{with_color('[YA COLOCADO]', BRIGHT_GREEN)} {with_color(user, BRIGHT_BLUE)} en "
                            f"{with_color(user.org_path_unit, BRIGHT_CYAN)}")
        else:
            logger.show_info(f"Añadiendo {with_color(user, BRIGHT_BLUE)} a {with_color(user.org_path_unit, BRIGHT_CYAN)}")

def generate_new_teachers(context: SchoolContext, delphos_teachers: List[Teacher]) -> List[Teacher]:
    new_teachers = []
    for teacher in delphos_teachers:
        if teacher not in context.all_google_users:
            teacher.org_path_unit = context.org_path_unit + "Profesores"
            teacher.generate_account_attributes(context.domain)
            change_email_if_needed(teacher, context.all_emails)
            logger.show_info(f"Creando {with_color(teacher.fullname + ' (' + teacher.email + ')', BRIGHT_BLUE)} "
                                f"en {with_color(teacher.org_path_unit, BRIGHT_CYAN)}")
            new_teachers.append(teacher)

    if not new_teachers:
        logger.show_warning("No hay profesores nuevos")

    return new_teachers

def generate_new_students(context: SchoolContext, course_delphos_students: List[Student], org_path) -> List[Student]:
    new_students = [student for student in course_delphos_students if student not in context.all_google_users]

    for student in new_students:
        student.org_path_unit = context.org_path_unit + org_path
        student.generate_account_attributes(context.domain)

        change_email_if_needed(student, context.all_emails)
        text = f"Creando {with_color(student, BRIGHT_BLUE)} en {with_color(student.org_path_unit, BRIGHT_CYAN)}"
        if student.enrollment_year == context.current_year:
            text = with_color("[NUEVA MATRÍCULA] ", BRIGHT_GREEN) + text
        else:
            text = with_color("[CASO EXTRAÑO] ", BRIGHT_MAGENTA) + text
        logger.show_info(text)

    if not new_students and course_delphos_students:
        logger.show_warning(f"No hay ningún alumno nuevo de {course_delphos_students[0].course}")
    elif not course_delphos_students:
        logger.show_error("No hay ningún alumno en la lista")

    return new_students

def write_new_students(context: SchoolContext, course_students: List[Student], org_path: str, filename: str) -> None:
    new_students = generate_new_students(context, course_students, org_path)
    if new_students:
        write_users(new_students, filename, context.fieldnames)

def write_new_teachers(context: SchoolContext, teachers: List[Teacher], filename: str) -> None:
    new_teachers = generate_new_teachers(context, teachers)
    if new_teachers:
        write_users(new_teachers, filename, context.fieldnames)

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
                    logger.show_error(f"Valor en csv de estudiante de delphos no permitido: {exc.args}")
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
            logger.show_error(f"Valor en csv de profesor de delphos no permitido: {exc.args}")
            sys.exit(1)

def generate_person_from_google(row: List[str]) -> SchoolPerson:
    person = None
    try:
        if len(row) != MAXIMUM_COLS_GOOGLE_CSV:
            raise IncorrectCsvValueError("Número de columnas en csv de google incorrecto", len(row))
        if row[5].split("/")[-1] == "Profesores":
            person = Teacher.from_google_csv(row)
        else:
            person = Student.from_google_csv(row)
    except IncorrectCsvValueError as exc:
        logger.show_error(f"Csv incorrecto {exc.args}")
        sys.exit(1)
    else:
        return person

def get_google_csv_data(filename: str) -> Tuple[str, Set[SchoolPerson]]:
    with open(filename) as csv_filename:
        csv_reader = csv.reader(csv_filename)
        all_google_users = set()
        fieldnames = next(csv_reader)

        for row in csv_reader:
            person = generate_person_from_google(row)
            all_google_users.add(person)

    return fieldnames, all_google_users

def create_context(args: argparse.Namespace, google_data: Tuple[str, Set[SchoolPerson]]) -> SchoolContext:
    domain = args.domain
    org_unit_path = f"/Curso {args.year}/"
    current_year = re.match(r"(\d+)[-/\s]\d+", args.year).group(1)

    fieldnames, all_google_users = google_data

    return SchoolContext(fieldnames, all_google_users, domain, org_unit_path, current_year)

def generate_new_teachers_command(args: argparse.Namespace, context: SchoolContext) -> None:
    all_teachers = load_teachers(args.teacher_csv_file)
    context.create_single_reference(all_teachers)

    if args.reallocate:
        def _warning_func(teacher: Teacher) -> None:
            logger.show_warning(f"El profesor {with_color(teacher, BRIGHT_BLUE)} está en Delphos pero no en Google Suite")

        generate_reallocated_users(context, all_teachers, "Profesores", _warning_func)
        write_users(all_teachers, args.output, context.fieldnames)

        lost_teachers = generate_lost_users(context, all_teachers, "Bajas/Profesores")
        write_users(lost_teachers, "bajas-profesores.csv", context.fieldnames)
    else:
        write_new_teachers(context, all_teachers, args.output)

def generate_new_students_command(args: argparse.Namespace, context: SchoolContext,
                                    course_to_students: Dict[str, Student]) -> None:

    def _warning_func(student: Student) -> None:
        logger.show_warning(f"El alumno {with_color(student, BRIGHT_BLUE)} de {with_color(student.course, BRIGHT_CYAN)}"
                                    " está en Delphos pero no en Google Suite")

    def _create_specific_course(course: str, unit_path: str) -> None:
        filename = os.path.join(args.output, course + ".csv")
        if course in course_to_students:
            if args.reallocate:
                generate_reallocated_users(context, course_to_students[course], unit_path, _warning_func)
                write_users(course_to_students[course], filename, context.fieldnames)
            else:
                write_new_students(context, course_to_students[course], unit_path, filename)
        else:
            logger.show_warning(f"No se ha encontrado el curso {course}")

    all_students = [student for course in course_to_students for student in course_to_students[course]]
    context.create_single_reference(all_students)

    if args.course_unit_csv:
        course_unit_paths = load_course_unit_path(args.course_unit_csv)
        for course, unit_path in course_unit_paths:
            _create_specific_course(course, unit_path)
    else:
        _create_specific_course(*args.manual)

    if args.reallocate:
        lost_students = generate_lost_users(context, all_students, "Bajas/Alumnos")
        write_users(lost_students, "bajas-alumnos.csv", context.fieldnames)

def main():
    args = get_args()
    context = create_context(args, get_google_csv_data(args.csv_google))

    if args.action == "generar-profesores":
        generate_new_teachers_command(args, context)
    elif args.action == "generar-alumnos":
        files_path = get_student_csv_filenames(args.students_directory)
        course_to_students = load_students(files_path)

        if not os.path.isdir(args.output):
            os.mkdir(args.output)
        generate_new_students_command(args, context, course_to_students)

    if args.log_filename:
        logger.write_log_file(args.log_filename)

if __name__ == "__main__":
    main()