
pip list
pip install virtualenv

Setup => virtualenv env
Start => ./env/Scripts/activate

[[TinyDB]]
db.purge()
  .insert()
  

```python 
import app
import pprint
from tinydb import Query

print("\n\n=== Print DB value (before purge)====")
pprint.pprint(app.db.all())

app.db.insert({
        "profile": "BMW",
        "img": "img.png",
        "detect": ["PERSON", "LOCATION", "NRP"],
        "key": "ABC",
        "password": "123",
        "uploads": [],
})

app.db.insert({
        "profile": "Audi",
        "img": "img3.png",
        "detect": ["PERSON", "ANIMAL"],
        "key": "GHI",
        "password": "789",
        "uploads": [],
})


print("\n\n=== Print DB value (after re-insert)====")
pprint.pprint(app.db.all())


print("\n\n=== Query stuff ====")
User = Query()
pprint.pprint(app.db.search(User.img == "img3.png"))
pprint.pprint(app.db.get(User.profile == "BMW"))

print("\n\n=== Update stuff ====")
app.db.update({"key": "XXXXXXXXXXX"}, User.profile == "BMW")
pprint.pprint(app.db.all())

print("\n\n=== detect value in arrray ====")
pprint.pprint(app.db.search(User.detect.any(["NRP"])))

app.db.truncate()
```

