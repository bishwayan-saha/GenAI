from pydantic import BaseModel, Field
from typing import Optional
from datetime import date 


class Pulse_PC_Ace(BaseModel):
    placement_dt: Optional[date] = Field()
    employee_cd: Optional[int] = Field(..., description="Unique employee code to identify an employee")
    employee_name: Optional[str] = Field(..., description="Full name of the employee")
    division_code: Optional[int] = Field(..., description="Unique code to identify a division")
    emp_division: Optional[str] = Field(..., description="Name of the division the employee works in")
    emp_position_code: Optional[int] = Field(..., description="Unique code to identify emp position")
    emp_designation: Optional[str] = Field(..., description="Designation of emp")
    emp_position: Optional[str] = Field(..., description="Position of employee")
    emp_hq_id: Optional[int] = Field(..., description="Unique id to identify the headquarter the employee belongs to")
    emp_hq_name: Optional[str] = Field(..., description="Headquarter name the employee belongs to")
    asm_emp_code: Optional[int] = Field(..., description="Unique code to identify ASM of the employee")
    asm_emp_name: Optional[str] = Field(..., description="Name of the ASM, considered as manager of the employee")
    asm_alignment_id: Optional[int] = Field(..., description="Unique id to identify the ASM alignment or position")

class Sku_Brand_Mapping(BaseModel):
    sku_code: Optional[int] = Field(..., description="Unique code to identify the product")
    product: Optional[str] = Field(..., description="Name of the product")
    division_code: Optional[int] = Field(..., description="Division code")
    material_type: Optional[str] = Field()
    vertical: Optional[int] = Field()
    brand_name: Optional[str] = Field(..., description="Brand name")
    division: Optional[str] = Field()
    brandid: Optional[str] = Field(..., description="Sub-brand ID")
    current_flag: Optional[str] = Field()
    width: Optional[int] = Field()
    mat_price : Optional[float]= Field(..., description="Price of the product")
    brand_classification: Optional[str] = Field(..., description="Type of brand ('Big', 'Divest', 'Invest(Nurture)')")
    sku_drop_flg: Optional[str] = Field(..., description="If the product is dropped or not")
    brand_code: Optional[int] = Field(..., description="Unique code of the brand")
    brand_rank: Optional[int] = Field(..., description="Ranking of the brand")

class Stockiest_HQ_Mapping_Ace(BaseModel):
    time_key: Optional[date] = Field()
    sold_to_party_id: Optional[int] = Field(..., description="Unique ID of the party to whom the product is sold")
    division_code: Optional[int] = Field(..., description="Unique division code")
    org_unit_id: Optional[int] = Field(..., description="Unique organization unit ID, which is equivalent to headquarter id")
    no_of_psrs: Optional[int] = Field()
    vacant_positions: Optional[int] = Field()

class Sales_Data(BaseModel):
    transaction_date: Optional[date] = Field(..., primary_key=True, description="Date when the product was sold")
    stockiest_id : Optional[int]= Field(..., primary_key=True, description="Unique ID of the stockiest, which references to sold_to_party_id of Stockiest_HQ_Mapping_Ace table")
    sku_code: Optional[int] = Field(..., description="Unique code of the product, which refers to sku_code of Sku_Brand_Mapping table")
    division_code: Optional[int] = Field(..., description="Unique division code, which refers to division_code of Sku_Brand_Mapping table")
    billing_type: Optional[str] = Field()
    sale_type: Optional[str] = Field(..., description="Sale type ('MEDVOL', 'Returns', 'Trade', 'Super Stockiest')")
    primary_sales: Optional[float] = Field(..., description="Sales value")
    primary_units: Optional[float] = Field(..., description="Sales unit (Total sales value = sales value * sales unit)")

class Targets_Data(BaseModel):
    time_key: Optional[date] = Field(..., primary_key=True, description="Target sales date")
    division_code: Optional[int] = Field(..., primary_key=True, description="Unique division code, which refres to division_code of Sku_Brand_Mapping & Sales_Data table")
    hq_code: Optional[int] = Field(..., description="Unique headquarter code")
    sku_code: Optional[int] = Field(..., description="Unique product code, which refers to sku_code of Sku_Brand_Mapping and Sales_Data table")
    target_units: Optional[float] = Field()
    target_value: Optional[float] = Field()
    sku_name: Optional[str] = Field(..., description="Product name")
    division_name: Optional[str] = Field(..., description="Division name")
    emp_hq_name: Optional[str] = Field(..., description="Employee HQ name, which refres to emp_hq_name of Pulse_PC_Ace table")


def get_schema_info(models: list[BaseModel]):
    schema_info = ""
    for model in models:
        schema_info += f"Table {model.__name__}:\n"
        for field_name, field in model.model_fields.items():
            description = field.description or "Self explanatory as per column name"
            data_type = field.annotation
            schema_info += f"    {field_name} ({data_type}): {description}\n"
        schema_info += "\n"
    return schema_info

# Example usage



