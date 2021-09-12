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

from typing import Dict, List, Mapping, Tuple, Set, Any

INVALID_CHARACTERS = "áéíóúñÁÉÍÓÚÑ"
REPLACEMENT_CHARACTERS = "aeiounAEIOUN"

PATH = "/Curso {}/"
DOMAIN = "@{}"
CURRENT_COURSE = ""

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

def with_color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="delphos_google_converter",
        description="Convierte csv generado por Delphos al csv que admite Google Suite"
    )

    parser.add_argument("csv_google", metavar="csv-google", help="Nombre del archivo csv de Google Suite")
    parser.add_argument("domain", metavar="dominio", help="Dominio del instituto (ej iesinsti.com)")
    parser.add_argument("year", metavar="año", help="Año del curso académico (ej 2021-2022)")

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

class SchoolPerson:

    def __init__(self, firstname: str, lastname: str):
        self.firstname = firstname
        self.lastname = lastname
        self.password = random_number_only_password(8)
        
        self.email: str = "{}" + DOMAIN
        self.org_path_unit = PATH

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

    def build_email_user(self) -> str:
        raise NotImplementedError("Método implementado en clases descendientes")

    @classmethod
    def from_csv(cls, csv_data: Any) -> SchoolPerson:
        raise NotImplementedError("Método implementado en clases descendientes")

    def __str__(self) -> str:
        return f"{self.firstname} {self.lastname} ({self.email})"

class Teacher(SchoolPerson):
    
    def __init__(self, firstname: str, lastname: str):
        super().__init__(firstname, lastname)
        self.email = self.email.format(self.build_email_user())
        self.org_path_unit += "Profesores"

    def build_email_user(self) -> str:
        first_surname = self.lastname.split()[0]
        return remove_all_accents(self.firstname[0].lower() + first_surname.lower())

    @classmethod
    def from_csv(cls, csv_data: str) -> Teacher:
        lastname, firstname = csv_data.split(", ")
        return cls(firstname.strip(), lastname.strip())

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email})")

class Student(SchoolPerson):

    def __init__(self, firstname: str, lastname: str, course: str, enrollment_id: str):
        super().__init__(firstname, lastname)
        self.enrollment_id = enrollment_id
        self.enrollment_year = enrollment_id.split("/")[0]
        self.course = course

        self.email = self.email.format(self.build_email_user())

    def build_email_user(self) -> str:
        first_surname = self.lastname.split()[0]
        user_name = remove_all_accents(self.firstname[0].lower() + first_surname.lower())
        # add the two last digit of the enrollment id. I did not choose this criteria to create emails. Someone
        # before me did it.
        user_name += self.enrollment_id[-2:]
        return user_name

    @classmethod
    def from_csv(cls, csv_data: List[str]) -> Student:
        lastname, firstname = csv_data[0].split(", ")
        course = "-".join(csv_data[1].split("º "))
        enrollment_id = csv_data[2]

        # strip just in case
        return cls(firstname.strip(), lastname.strip(), course.strip(), enrollment_id.strip())

    def __repr__(self):
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email}, course={self.course}, "
                f"enrollment_id={self.enrollment_id})")

def write_teachers_csv(teachers: List[Teacher], csv_filename: str,
                        fieldnames: str, all_names: Set[str]) -> None:
    with open(csv_filename, "w") as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames)
        csv_writer.writeheader()
        for teacher in teachers:
            if teacher.fullname not in all_names:
                print(f"Creando {teacher} en {teacher.org_path_unit}")
                csv_writer.writerow(teacher.as_csv_dict())


def write_student_course_csv(course_students: List[Student], org_path: str,
                            fieldnames: str, all_names: str, filename: str):

    non_existant_students = [student for student in course_students if student.fullname not in all_names]

    if non_existant_students:
        with open(filename, "w") as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames)
            csv_writer.writeheader()
            for student in non_existant_students:
                student.org_path_unit += org_path
                text = f"{student} en {student.org_path_unit}"
                if student.enrollment_year == CURRENT_COURSE:
                    text = with_color("[NUEVA MATRÍCULA] ", BRIGHT_GREEN) + text
                print(text)
                csv_writer.writerow(student.as_csv_dict())
    elif course_students:
        print(with_color(f"No hay ningún alumno nuevo de {course_students[0].course}", BRIGHT_YELLOW))
    else:
        print(with_color("ERROR: La lista 'course_students' no tiene ningún estudiante"), BRIGHT_RED)

def get_student_csv_filenames(directory: str) -> List[str]:
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".csv")]

def load_students(csv_filenames: List[str]) -> Dict[str, Student]:
    course_to_student = {}

    for csv_filename in csv_filenames:
        with open(csv_filename, encoding="latin_1") as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)
            for row in csv_reader:
                student = Student.from_csv(row[:3])
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
        return [Teacher.from_csv(data[0]) for data in csv_reader]

def get_google_csv_data(filename: str) -> Tuple[str, Set[str]]:
    with open(filename) as csv_filename:
        csv_reader = csv.reader(csv_filename)
        all_names = set()

        fieldnames = next(csv_reader)

        for row in csv_reader:
            name = f"{row[0].strip()} {row[1].strip()}"
            all_names.add(name)

    return (fieldnames, all_names)


def main():
    global DOMAIN, PATH, CURRENT_COURSE

    args = get_args()

    # these two global won't change anymore
    DOMAIN = DOMAIN.format(args.domain)
    # TODO: it is more robust a regex rule for this
    CURRENT_COURSE = args.year.split("-")[0]
    PATH = PATH.format(args.year)

    fieldnames, all_names = get_google_csv_data(args.csv_google)

    if args.action == "generar-profesores":
        all_teachers = load_teachers(args.teacher_csv_file)
        write_teachers_csv(all_teachers, args.output, fieldnames, all_names)
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
                    write_student_course_csv(
                        course_to_students[course], unit_path, fieldnames, all_names, filename
                    )
                else:
                    print(with_color(f"ERROR: No se ha encontrado el curso {course}", BRIGHT_RED))
        else:
            course, unit_path = args.manual
            filename = os.path.join(args.output, course + ".csv")
            if course not in course_to_students:
                write_student_course_csv(
                    course_to_students[course], unit_path, fieldnames, all_names, filename
                )
            else:
                print(with_color(f"ERROR: No se ha encontrado el curso {course}", BRIGHT_RED))
if __name__ == "__main__":
    main()