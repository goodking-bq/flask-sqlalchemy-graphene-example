> this is an example for flask + sqlalchemy + graphql
# run this example
```shell

> git clone https://github.com/goodking-bq/flask-sqlalchemy-graphene-example.git
> cd flask-sqlalchemy-graphene-example
> pipenv install -d   # install requirements

> export FLASK_APP=run.py

> flask db init # init db
> flask db migrate
> flask db upgrade # init db end

> flask run

> # or run in docker 
> docker run -p 5000:5000 goldenz/flask-sqlalchemy-graphene-example
```

> now you can visit this [url](http://127.0.0.1:5000/graphql)

# feature

- add `offset` `limit` `totalCount` to pagination
- auto add `dbId` for model's database id
- just edit your model, auto genarate query `model`,`modelList` and mutation `createModel`,`updateModel`,`deleteModel`
- mutation auto return `ok` for success,`message` for more information and `output` for model data

# Tutorial
read the code [example_app](https://github.com/goodking-bq/flask-sqlalchemy-graphene-example)
and this this file [graphene.py](https://github.com/goodking-bq/flask-sqlalchemy-graphene-example/blob/master/example_app/utils/graphene.py) is very import.

# Query and Mutation example

1. ## create a role and user
```graphql
mutation{
  createRole(input:{name:"admin"}){
    ok
    message
    output{
      name
      id
    }
  }
  createUser(input:{name:"golden",password: "goldenpwd"}){
    ok
    message
    output{
      id
      name
      password
    }
  }
}
```
you well get this return:
```json
{
  "data": {
    "createRole": {
      "ok": true,
      "message": "操作成功",
      "output": {
        "name": "admin",
        "id": "Um9sZU91dHB1dFR5cGU6MQ=="
      }
    },
    "createUser": {
      "ok": true,
      "message": "操作成功",
      "output": {
        "id": "VXNlck91dHB1dFR5cGU6Mg==",
        "name": "golden",
        "password": "goldenpwd"
      }
    }
  }
}
```

2. ## update user role

```graphql
mutation{
  updateUser(id:"VXNlck91dHB1dFR5cGU6Mg==", input:{roles:["Um9sZU91dHB1dFR5cGU6MQ=="],password:"aaa",name:"changename"}){
    ok
    message
    output{
      id
      name
      roles{
        edges{
          node{
            name
            id
          }
        }
      }
    }
  }
}
```
and got this
```json
{
  "data": {
    "updateUser": {
      "ok": true,
      "message": "操作成功",
      "output": {
        "id": "VXNlck91dHB1dFR5cGU6Mg==",
        "name": "changename",
        "roles": {
          "edges": [
            {
              "node": {
                "name": "admin",
                "id": "Um9sZU91dHB1dFR5cGU6MQ=="
              }
            }
          ]
        }
      }
    }
  }
}
```
3. ## query and pagination,use `offset`,`limit`,`totalCount`
```graphql
query{
  userList(offset:0,limit:2){
    totalCount
    edges{
      node{
        id
        name
      }
    }
  },
  roleList{
    totalCount
    edges{
      node{
        id
        name
      }
    }
  }
}
```
result is :
```json
{
  "data": {
    "userList": {
      "totalCount": 1,
      "edges": [
        {
          "node": {
            "id": "VXNlck91dHB1dFR5cGU6MQ==",
            "name": "changename"
          }
        }
      ]
    },
    "roleList": {
      "totalCount": 1,
      "edges": [
        {
          "node": {
            "id": "Um9sZU91dHB1dFR5cGU6MQ==",
            "name": "admin"
          }
        }
      ]
    }
  }
}
```

# Read More
- [Graphene](https://graphene-python.org/)
- [Graphene for Python](https://github.com/graphql-python/graphene)
- [SQLAlchemy](http://www.sqlalchemy.org/)
- [graphene-sqlalchemy](https://github.com/graphql-python/graphene-sqlalchemy)
- [flask-graphql](https://github.com/graphql-python/flask-graphql)


# Thanks for
[qubitron's code](https://gist.github.com/qubitron/6e7d48667a05120dc58bdfd0516b3980)