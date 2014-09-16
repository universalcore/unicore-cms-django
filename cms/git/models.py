from unicore_gitmodels import models
from cms import utils

ws = utils.get_git_workspace()
GitPage = ws.register_model(models.GitPageModel)
GitCategory = ws.register_model(models.GitCategoryModel)
