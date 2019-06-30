
def basic_check(r):
    print(r.json())
    assert r.status_code == 200
    assert len(r.json()) > 0

