from rest_framework_simplejwt.tokens import RefreshToken


def issue_token_pair(user, session):
    """Emite access+refresh con el claim `sid` (id de la `Session`), para poder revocar sesiones
    específicas sin depender de la blacklist genérica de simplejwt."""
    refresh = RefreshToken.for_user(user)
    refresh['sid'] = str(session.id)
    access = refresh.access_token
    access['sid'] = str(session.id)
    return {'access': str(access), 'refresh': str(refresh)}
