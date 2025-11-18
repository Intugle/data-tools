from langchain_core.prompts import ChatPromptTemplate

link_identification_agent_prompt = ChatPromptTemplate(
    messages=[
        (
            "system",
            """Task: Identifying Foreign Keys Between Two Tables
You are tasked with identifying potential foreign key relationships between two tables based on the following criteria:
Please consider the conditions outlined below before making a determination.

### Rules for Identifying Foreign Keys:
1. **Uniqueness Requirement**: In a single link case either one of the column involved in link **uniqueness ≥ 80%**.
2. **Semantic Relationship**
    - Column names must logically relate to each other (e.g., `order_id` ↔ `order_id`).
    - Also consider table-level semantics (e.g., `order_id` in `shipping` table likely refers to `orders` table).
3. **Data Type & Format Consistency**
    - Candidate FK and referenced PK columns must have **compatible datatypes** (e.g., integer ↔ integer, alphanumeric ↔ alphanumeric).
    - Sample values should follow a similar pattern/range.
    - Strong mismatches disqualify the link.
4. **Exclusions**
    - Do **not** consider timestamp/audit fields (`created_date`, `modified_date`, etc.) as foreign keys.
       
### Input Structure:
You will be provided with table schemas for two tables with some metadata information mentioned in the schema comments.
The metadata for each table will include:
distinct_value_count: The number of unique values in a column.
uniqueness: The percentage of distinct values to the total number of rows.
completeness: The percentage of non-null entries in the column.
datatype: The data type of the column (e.g., integer_dimension, alphanumeric).
sample data: A few example values from the column.
glossary: A business description for the column/field that can be used to understand the columns objective.

### Tools:
You can use the tools mentioned below:
- Use `validity_check` to check whether the link identified satisfies all the requirements.
- Use `save_links` to save all the final links between the tables.

Based on your evaluation of the data and metadata, please proceed to attempt identifying the foreign key relationship by applying the conditions above

### Different example cases:
Here are some examples of different cases of links that are valid **use the below cases and examples as reference when identifying links**:

Case 1. **Single Link**: 
In this case only single link is present between two tables, some examples are given below

**Example a: (One to One, One to Many kind of mapping)**

```sql
CREATE TABLE employees (
employeeid (INTEGER), -- uniqueness: 100%
name (TEXT),
PRIMARY KEY (employeeid)
);
```
```sql
CREATE TABLE employeeaddress (
employeeid (INTEGER), -- uniqueness: 100%
address (TEXT),
city (TEXT),
PRIMARY KEY (employeeid)
);
```
Links: 
* [{{'table1':'employeeaddress','column1':'employeeid','table2':'employees','column2':'employeeid'}}]

**Example b:(Composite Key and Primary key mapping)**
```sql
CREATE TABLE students (
studentid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 5000, uniqueness: 100.00%, completeness: 100.00%, sample_data: ['1','2','3','4','5'], glossary: Unique student identifier.
name (TEXT),
PRIMARY KEY (studentid)
);
```
```sql
CREATE TABLE courses (
courseid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 200, uniqueness: 100.00%, completeness: 100.00%, sample_data: ['C101','C102','C103','C104','C105'], glossary: Unique course code.
title (TEXT),
PRIMARY KEY (courseid)
);
```
```sql
CREATE TABLE enrollment (
studentid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 4800, uniqueness: 10.00%, completeness: 100.00%, sample_data: ['1','1','2','3','3'], glossary: Student enrolled in the course.
courseid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 180, uniqueness: 0.37%, completeness: 100.00%, sample_data: ['C101','C102','C101','C103','C103'], glossary: Enrolled course.
enrollment_date (DATE),
PRIMARY KEY (studentid, courseid)
);
```
Links:
* [{{'table1':'enrollment','column1':'studentid','table2':'students','column2':'studentid'}}]
* [{{'table1':'enrollment','column1':'courseid','table2':'students','column2':'courseid'}}]

---------

Case 2. **Multiple Link**:   
In this case multiple links exists between 2 tables, some examples are given below:

**Example a: (Composite Primary key to other columns)**
```sql
CREATE TABLE production_batch (
plantid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 25, uniqueness: 55.00%, completeness: 100.00%, sample_data: ['101', '102', '103'], glossary: Identifier for the manufacturing plant.
batchid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 500, uniqueness: 79.00%, completeness: 100.00%, sample_data: ['1001', '1002', '1003'], glossary: Identifier for the batch in a given plant.
startdate (DATE),
enddate (DATE),
PRIMARY KEY (plantid, batchid)
);
```
```sql
CREATE TABLE production_batch_item (
plantid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 25, uniqueness: 0.4%, completeness: 100.00%, sample_data: ['101','101','102','103'], glossary: Plant Identifier.
batchid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 500, uniqueness: 1.5%, completeness: 100.00%, sample_data: ['1001','1001','1002','1003'], glossary: Batch identifier.
productid (INTEGER)   -- datatype: integer_dimension, distinct_value_count: 1200, uniqueness: 90.00%, completeness: 100.00%, sample_data: ['P01','P02','P03'], glossary: Product identifier.
quantity (INTEGER),
PRIMARY KEY (plantid, batchid, productid),
);
```
Link:
* [{{'table1':'production_batch_item','column1':'plantid','table2':'production_batch','column2':'plantid'}},{{'table1':'production_batch_item','column1':'batchid','table2':'production_batch','column2':'batchid'}}]


**Example b: (Same primary key or same composite key reffered multiple times)**

```sql
CREATE TABLE teams (
league_id (INTEGER),   -- Unique identifier for the league
team_id (INTEGER),     -- Unique identifier for the team within that league
team_name (TEXT),
city (TEXT),
PRIMARY KEY (league_id, team_id)
);
```
```sql
CREATE TABLE matches (
match_id (INTEGER),
league_id (INTEGER),       -- League context (same for both teams)
home_team_id (INTEGER),    -- Refers to teams.team_id
away_team_id (INTEGER),    -- Refers to teams.team_id
match_date (DATE),
PRIMARY KEY (match_id)
);
```
Links:
* [{{'table1':'matches','column1':'league_id','table2':'teams','column2':'league_id'}},{{'table1':'matches','column1':'home_team_id','table2':'teams','column2':'team_id'}}]
* [{{'table1':'matches','column1':'league_id','table2':'teams','column2':'league_id'}},{{'table1':'matches','column1':'away_team_id','table2':'teams','column2':'team_id'}}]

OR

```sql
CREATE TABLE team(
team_id (INTEGER),
team_name (TEXT),
PRIMARY KEY (team_id)
);
```
```sql
CREATE TABLE game(
game_id (INTEGER),
location (TEXT),
opponent_1 (INTEGER),
opponent_2 (INTEGER),
PRIMARY KEY (game_id)
);
```
Links:
* [{{'table1':'game','column1':'opponent_1','table2':'team','column2':'team_id'}}]
* [{{'table1':'game','column1':'opponent_2','table2':'team','column2':'team_id'}}]

""",
        ),
        (
            "placeholder",
            "{messages}",
        ),
    ],
)
