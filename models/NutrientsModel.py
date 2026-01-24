from pydantic import BaseModel, Field

#
# 栄養素データモデル
#
class NutrientsModel(BaseModel):
    kcal: int = Field(description="Food calories are a measure of how much energy your body gets from what you eat")
    carbo: float = Field(description="amount of carbo")
    lipid: float = Field(description="amount of lipid")
    protein: float = Field(description="amout of protein")