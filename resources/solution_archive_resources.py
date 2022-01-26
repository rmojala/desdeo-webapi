from app import db

from copy import deepcopy
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, reqparse
from models.user_models import UserModel
from models.problem_models import SolutionArchive, Problem
import simplejson as json

# For POST and PUT
archive_parser_add = reqparse.RequestParser()
archive_parser_add.add_argument(
    "problem_id",
    type=int,
    help="'problem_id' is required.",
    required=True,
)
archive_parser_add.add_argument(
    "variables",
    type=str,
    help="'variables' missing.",
    required=True,
)
archive_parser_add.add_argument(
    "objectives",
    type=str,
    help="'objectives' required.",
    required=True,
)
archive_parser_add.add_argument(
    "append",
    type=bool,
    help="Whether to append the supplied solutions to the existing archive. Defaults to true",
    default=True,
    required=False,
)

# For GET
archive_parser_get = reqparse.RequestParser()
archive_parser_get.add_argument(
    "problem_id",
    type=int,
    help="'problem_id' is required.",
    required=True,
)


class Archive(Resource):
    @jwt_required()
    def post(self):
        data = archive_parser_add.parse_args()

        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        problem_ids = [problem.id for problem in Problem.query.filter_by(user_id=current_user_id).all()]

        # check that supplied problem_id exists for user
        if data["problem_id"] not in problem_ids:
            msg = f"No problem with id {data['problem_id']} exists for current user."
            return {"message": msg}, 404

        problem_id = data["problem_id"]

        # check that variables and objectives are of same length
        variables = json.loads(data["variables"])
        objectives = json.loads(data["objectives"])
        if len(variables) != len(objectives):
            msg = (
                f"Number of variables vectors supplied ({len(variables)}) do not match the "
                f"number of objective vectors supplied {len(objectives)}."
            )
            return {"message": msg}, 400

        # check if old solutions exists
        archive_query = SolutionArchive.query.filter_by(problem_id=problem_id).first()

        if archive_query is None:
            # add supplied solutions to new archive
            new_solutions = {
                "variables": variables,
                "objectives": objectives,
            }
            db.session.add(SolutionArchive(problem_id=problem_id, solutions_dict_pickle=new_solutions))
            db.session.commit()

            msg = f"Created new archive for problem with id {problem_id} and added solutions."
            return {"message": msg}, 201
        else:
            if data["append"]:
                # add supplied solutions to existing archive
                solutions = deepcopy(archive_query.solutions_dict_pickle)
                solutions["variables"] += variables
                solutions["objectives"] += objectives
                msg = f"Appended solutions to existing archive for problem with id f{problem_id}"
            else:
                # add only new, delete old
                solutions = {"variables": variables, "objectives": objectives}
                msg = f"Replaced solutions in existing archive for problem with id f{problem_id}"

            # need to make deepcopy to have a new mem addres so that sqlalchemy updates the pickle
            # TODO: use a Mutable column
            archive_query.solutions_dict_pickle = solutions
            db.session.commit()

            return {"message": msg}, 202

    @jwt_required()
    def get(self):
        data = archive_parser_get.parse_args()

        current_user = get_jwt_identity()
        current_user_id = UserModel.query.filter_by(username=current_user).first().id

        problem_ids = [problem.id for problem in Problem.query.filter_by(user_id=current_user_id).all()]

        # check that supplied problem_id exists for user
        if data["problem_id"] not in problem_ids:
            msg = f"No problem with id {data['problem_id']} exists for current user."
            return {"message": msg}, 404

        problem_id = data["problem_id"]

        query = SolutionArchive.query.filter_by(problem_id=problem_id).first()

        # check query to be non empty
        if query is None:
            # query empty
            msg = f"No archive found for problem with id {problem_id}"
            return {"message": msg}, 404

        # query not empty
        dict_data = query.solutions_dict_pickle

        return {"variables": dict_data["variables"], "objectives": dict_data["objectives"]}, 200