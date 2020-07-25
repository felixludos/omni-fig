
import omnifig as fig


def test_create_obj():
	
	A = fig.get_config()
	
	A.a.b.c = 10
	
	assert 'a' in A
	assert 'b' in A.a
	assert 'c' in A.a.b
	assert type(A) == type(A.a)
	assert A.a.b.c == 10

