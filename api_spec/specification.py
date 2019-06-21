from api_spec.swagger import Swagger
from enum import Enum

class Specification(Enum):
    SWAGGER = Swagger

    def url(self,url):
        return self.value(url)