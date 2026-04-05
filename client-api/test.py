from competition.fetch_competition import COMPETITION
from competition.fetch_competition_list import COMPETITION_LIST_STORE

x = COMPETITION_LIST_STORE.get()
y = COMPETITION.get("0001da7a-7fa8-471b-b131-6ada4b45fb2f")
print(x)
