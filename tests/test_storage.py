import ast
import csv
import json
import pytest

from collections import Counter

from firepit.exceptions import IncompatibleType
from firepit.exceptions import UnknownViewname

from .helpers import tmp_storage


def test_local(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', fake_bundle_file)

    store.extract('urls', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls = store.values('url:value', 'urls')
    print(urls)
    assert len(urls) == 14
    assert 'http://www8.example.com/page/176' in urls
    assert 'http://www27.example.com/page/64' not in urls

    store.delete()


def test_in_memory(fake_bundle_file, tmpdir):
    with open(fake_bundle_file, 'r') as fp:
        bundle = json.loads(fp.read())

    store = tmp_storage(tmpdir)
    store.cache('q1', bundle)

    store.extract('urls', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls = store.values('url:value', 'urls')
    print(urls)
    assert len(urls) == 14
    assert 'http://www8.example.com/page/176' in urls
    assert 'http://www27.example.com/page/64' not in urls

    store.delete()


def test_basic(fake_bundle_file, fake_csv_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    store.extract('urls', 'url', 'q1', "[ipv4-addr:value ISSUBSET '192.168.0.0/16']")
    urls = store.values('url:value', 'urls')
    print(urls)
    assert len(urls) == 31
    assert 'http://www27.example.com/page/64' in urls
    assert store.count('urls') == 31

    urls1 = store.lookup('urls', limit=5)
    assert len(urls1) == 5
    urls2 = store.lookup('urls', limit=5, offset=2, cols="value,number_observed")
    assert len(urls2) == 5
    assert len(urls2[1].keys()) == 2
    assert 'number_observed' in urls2[1].keys()

    store.assign('sorted', 'urls', op='sort', by='value')
    urls = store.values('url:value', 'sorted')
    print('sorted:', urls)
    assert len(urls) == 31
    assert urls[0] == 'http://www11.example.com/page/108'

    # Now try to change urls, even though sorted is defined using it
    store.extract('urls', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls = store.values('url:value', 'urls')
    print('reused:', urls)
    assert len(urls) == 14
    sorted_urls = store.values('url:value', 'sorted')
    print('sorted:', sorted_urls)
    assert len(sorted_urls) == 14  # Also changes...weird

    store.extract('a_ips', 'ipv4-addr', 'q1', "[ipv4-addr:value LIKE '10.%']")
    a_ips = store.values('ipv4-addr:value', 'a_ips')
    print(a_ips)
    assert len(a_ips) == 100
    assert '10.0.0.141' in a_ips

    store.extract('a_ips', 'ipv4-addr', 'q1', "[ipv4-addr:value LIKE '10.%']")
    a_ips = store.values('ipv4-addr:value', 'a_ips')
    print(a_ips)
    assert len(a_ips) == 100
    assert '10.0.0.141' in a_ips

    store.extract('users', 'user-account', 'q1', "[ipv4-addr:value LIKE '10.%']")
    users = store.values('user-account:account_login', 'users')
    print(users)
    assert len(users) == 100
    counter = Counter(users)
    assert counter['henry'] == 2
    assert counter['isabel'] == 12
    by = 'user-account:account_login'
    store.assign('grouped_users', 'users', op='group', by=by)
    cols = store.columns('grouped_users')
    _, _, by = by.rpartition(':')
    assert f'unique_{by}' not in cols
    grouped_users = store.lookup('grouped_users')
    print(grouped_users)
    henry = next((item for item in grouped_users if item['account_login'] == 'henry'), None)
    assert henry
    assert henry['number_observed'] == 2
    isabel = next((item for item in grouped_users if item['account_login'] == 'isabel'), None)
    assert isabel
    assert isabel['number_observed'] == 12

    with open(fake_csv_file, newline='') as fp:
        reader = csv.DictReader(fp)
        def infer_type(value):
            try:
                return ast.literal_eval(value)
            except Exception:
                return value
        data = [{key: infer_type(val) for key, val in row.items()} for row in reader]
        res = store.load('test_procs', data)
        assert res == 'process'
    rows = store.lookup('test_procs')
    assert len(rows) == 5
    assert isinstance(rows[0]['pid'], int)
    ids = [row['id'] for row in rows]
    assert 'process--41eb677f-0335-49da-98b8-375e22f8c94e_0' in ids
    assert 'process--0bb2e61f-8c88-415d-bb7a-bcffc991c38e_0' in ids
    #assert rows[1]['binary_ref.parent_directory_ref.path'] == 'C:\\Windows\\System32'
    #assert rows[2]['parent_ref.command_line'] == 'C:\\windows\\system32\\cmd.exe /c "reg delete HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run /v caldera /f"'

    ips = ['10.0.0.1', '10.0.0.2']
    res = store.load('test_ips', ips, sco_type='ipv4-addr')
    assert res == 'ipv4-addr'
    rows = store.lookup('test_ips')
    assert len(rows) == 2
    for row in rows:
        assert row['type'] == 'ipv4-addr'
        assert row['value'] in ips

    store.delete()
    store = tmp_storage(tmpdir)
    assert len(store.tables()) == 0


def test_join(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('local_ips', 'ipv4-addr', 'q1', "[ipv4-addr:value LIKE '%']")

    res = store.load('test_ips', [
        {
            'type': 'ipv4-addr',
            'value': '10.0.0.201',
            'risk': 'high',
        },
        {
            'type': 'ipv4-addr',
            'value': '10.0.0.214',
            'risk': 'high',
        }
    ])

    store.join('marked', 'local_ips', 'value', 'test_ips', 'value')
    rows = store.lookup('marked')
    assert 'value' in rows[0]
    assert 'risk' in rows[0]
    for row in rows:
        if row['value'] in ['10.0.0.201', '10.0.0.214']:
            assert row['risk'] == 'high'
        else:
            assert row['risk'] is None


@pytest.mark.parametrize(
    'sco_type, prop, op, value, expected, unexpected', [
        ('url', 'value', 'LIKE', '%example.com/page/1%', 'http://www26.example.com/page/176', 'http://www67.example.com/page/264'),
        ('url', 'value', 'MATCHES', '^.*example.com/page/1[0-9]*$', 'http://www26.example.com/page/176', 'http://www67.example.com/page/264'),
        ('ipv4-addr', 'value', 'ISSUBSET', '10.0.0.0/8', '10.0.0.141', '192.168.212.97'),
        ('ipv4-addr', 'value', '=', '10.0.0.141', '10.0.0.141', '192.168.212.97'),
        ('network-traffic', 'dst_port', '<=', 1024, 22, 3128),
        ('user-account', 'account_login', 'IN', ('alice', 'bob', 'carol'), 'bob', 'david'),
        ('network-traffic', 'dst_ref.value', 'ISSUBSET', '10.0.0.0/25', '10.0.0.73', '10.0.0.197'),
    ]
)
def test_ops(fake_bundle_file, tmpdir, sco_type, prop, op, value, expected, unexpected):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    if isinstance(value, str):
        value = f"'{value}'"
    store.extract('data', sco_type, 'q1', f"[{sco_type}:{prop} {op} {value}]")
    data = store.values(f"{sco_type}:{prop}", 'data')
    assert expected in data
    assert unexpected not in data

    # Try the negation when appropriate
    if op in ['IN', 'LIKE', 'MATCHES', 'ISSUBSET', 'ISSUPERSET']:
        store.extract('data', sco_type, 'q1', f"[{sco_type}:{prop} NOT {op} {value}]")
        data = store.values(f"{sco_type}:{prop}", 'data')
        assert unexpected in data
        assert expected not in data


def test_grouping(fake_bundle_file, fake_csv_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    store.extract('conns', 'network-traffic', 'q1', "[network-traffic:dst_port < 1024]")
    store.assign('conns', 'conns', op='group', by='src_ref.value')
    srcs = store.values('src_ref.value', 'conns')
    assert srcs

    groups = store.lookup('conns')
    assert groups
    assert 'unique_dst_port' in groups[0].keys()


def test_extract(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    store.extract('conns', 'network-traffic', 'q1', "[network-traffic:dst_port < 1024]")
    store.assign('conns', 'conns', op='group', by='src_ref.value')
    srcs = store.values('src_ref.value', 'conns')
    assert srcs

    groups = store.lookup('conns')
    assert groups
    assert 'unique_dst_port' in groups[0].keys()


def test_schema(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    schema = store.schema('url')
    print(schema)
    columns = [i['name'] for i in schema]
    assert 'id' in columns
    assert 'type' in columns
    assert 'value' in columns


def test_filter(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('urls', 'url', 'q1', "[url:value LIKE '%page/1%']")
    store.filter('urls', 'url', 'urls', "[url:value = 'http://www20.example.com/page/19']")
    urls = store.values('url:value', 'urls')
    assert len(urls) == 1
    assert 'http://www20.example.com/page/19' == urls[0]
    views = store.views()
    assert len(views) == 1
    assert views[0] == 'urls'


def test_filter2(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('ssh_conns', 'network-traffic', 'q1', "[network-traffic:dst_port = 22]")
    store.filter('ssh_ips', 'ipv4-addr', 'ssh_conns', "[network-traffic:dst_port = 22]")
    ssh_conns = store.lookup('ssh_conns')
    assert len(ssh_conns) == 29
    ssh_ips = store.lookup('ssh_ips')
    assert len(ssh_ips) == 29 # BUG?: * 2
    views = store.views()
    assert len(views) == 2


def test_reassign(fake_bundle_file, fake_csv_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    store.extract('urls', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls = store.lookup('urls')
    assert len(urls) == 14
    #print(json.dumps(urls, indent=4))

    # Simulate running some analytics to enrich these
    for url in urls:
        url['x_enrich'] = 1

    # Now reload into a new var
    store.reassign('enriched_urls', urls)
    rows = store.lookup('__membership')
    print(json.dumps(rows, indent=4))
    rows = store.lookup('enriched_urls')
    print(json.dumps(rows, indent=4))
    assert len(rows) == len(urls)

    # Make sure original var isn't modified
    urls = store.lookup('urls')
    assert len(urls) == 14

    # Original var's objects should have been updated
    assert urls[0]['x_enrich'] == 1


def test_appdata(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('ssh_conns', 'network-traffic', 'q1', "[network-traffic:dst_port = 22]")
    data = {'foo': 99}
    store.set_appdata('ssh_conns', json.dumps(data))
    result = json.loads(store.get_appdata('ssh_conns'))
    assert data['foo'] == result['foo']
    assert len(result) == len(data)

    store2 = tmp_storage(tmpdir)
    result = json.loads(store2.get_appdata('ssh_conns'))
    assert data['foo'] == result['foo']
    assert len(result) == len(data)


def test_viewdata(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('ssh_conns', 'network-traffic', 'q1', "[network-traffic:dst_port = 22]")
    ssh_data = {'foo': 99}
    store.set_appdata('ssh_conns', json.dumps(ssh_data))
    store.extract('dns_conns', 'network-traffic', 'q1', "[network-traffic:dst_port = 53]")
    dns_data = {'bar': 98}
    store.set_appdata('dns_conns', json.dumps(dns_data))

    results = store.get_view_data(['ssh_conns', 'dns_conns'])
    assert len(results) == 2
    for result in results:
        if result['name'] == 'ssh_conns':
            assert ssh_data == json.loads(result['appdata'])
        else:
            assert dns_data == json.loads(result['appdata'])


def test_duplicate(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)

    # Query once
    store.cache('q1', [fake_bundle_file])
    store.extract('urls1', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls1 = store.values('url:value', 'urls1')

    # Now query again - not reasonable, but simulates getting duplicate IDs from different sources
    store.cache('q2', [fake_bundle_file])
    store.extract('urls2', 'url', 'q2', "[url:value LIKE '%page/1%']")
    urls2 = store.values('url:value', 'urls2')

    assert len(urls1) == len(urls2)


def test_sort_same_name(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])
    store.extract('urls', 'url', 'q1', "[ipv4-addr:value ISSUBSET '192.168.0.0/16']")
    urls1 = store.values('url:value', 'urls')
    print(urls1)
    assert len(urls1) == 31
    store.assign('urls', 'urls', op='sort', by='value')
    urls2 = store.values('url:value', 'urls')
    print(urls2)
    assert len(urls2) == 31
    assert set(urls1) == set(urls2)


def test_merge(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)

    store.cache('test-bundle', [fake_bundle_file])
    all_urls = set(store.values('url:value', 'url'))

    store.extract('urls1', 'url', 'test-bundle', "[url:value LIKE '%page/1%']")
    urls1 = set(store.values('url:value', 'urls1'))

    store.extract('urls2', 'url', 'test-bundle', "[url:value NOT LIKE '%page/1%']")
    urls2 = set(store.values('url:value', 'urls2'))

    assert urls1 | urls2 == all_urls

    store.merge('merged', ['urls1', 'urls2'])
    merged = set(store.values('url:value', 'merged'))
    assert merged == all_urls


@pytest.mark.skip(reason="this only happens with postgresql")
def test_change_type(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', [fake_bundle_file])

    # Create a var `foo` of type url
    store.extract('foo', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls = store.values('url:value', 'foo')
    print(urls)
    assert len(urls) == 14

    # Create a var `sorted_foo` of type url that depends on `foo`
    store.assign('sorted_foo', 'foo', op='sort', by='value')

    # sqlite3 doesn't have issues with this; only PostgreSQL
    with pytest.raises(IncompatibleType):
        store.extract('foo', 'ipv4-addr', 'q1', "[ipv4-addr:value ISSUBSET '192.168.0.0/16']")


def test_remove(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', fake_bundle_file)

    store.extract('urls1', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls1 = store.lookup('urls1')
    assert len(urls1) == 14

    store.extract('urls2', 'url', 'q1', "[url:value LIKE '%page/2%']")
    urls2 = store.lookup('urls2')
    assert len(urls2)

    store.remove_view('urls1')
    with pytest.raises(UnknownViewname):
        store.lookup('urls1')

    urls2 = store.lookup('urls2')
    assert len(urls2)


def test_rename(fake_bundle_file, tmpdir):
    store = tmp_storage(tmpdir)
    store.cache('q1', fake_bundle_file)

    store.extract('urls1', 'url', 'q1', "[url:value LIKE '%page/1%']")
    urls1 = store.lookup('urls1')
    assert len(urls1) == 14

    store.rename_view('urls1', 'urls2')
    with pytest.raises(UnknownViewname):
        store.lookup('urls1')

    urls2 = store.lookup('urls2')
    assert len(urls2) == 14


@pytest.mark.parametrize(
    'names', [
        (['urls1']),
        (['urls2']),
        (['urls1', 'urls2']),
    ]
)
def test_remove_after_merge(fake_bundle_file, tmpdir, names):
    store = tmp_storage(tmpdir)

    store.cache('test-bundle', [fake_bundle_file])
    all_urls = set(store.values('url:value', 'url'))

    store.extract('urls1', 'url', 'test-bundle', "[url:value LIKE '%page/1%']")
    urls1 = set(store.values('url:value', 'urls1'))

    store.extract('urls2', 'url', 'test-bundle', "[url:value NOT LIKE '%page/1%']")
    urls2 = set(store.values('url:value', 'urls2'))

    assert urls1 | urls2 == all_urls

    store.merge('merged', ['urls1', 'urls2'])

    # Remove the views we merged
    for name in names:
        store.remove_view(name)

    merged = set(store.values('url:value', 'merged'))
    assert merged == all_urls
