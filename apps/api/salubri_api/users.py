# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gestion des comptes de la mairie en ligne de commande.

    python -m salubri_api.users add <login> --role admin|moderateur [--name "Nom affiché"]
    python -m salubri_api.users passwd <login>
    python -m salubri_api.users disable <login>
    python -m salubri_api.users list

Le mot de passe est demandé au clavier (jamais en argument, il resterait dans l'historique) ; pour un script,
le passer sur l'entrée standard : `echo "$MDP" | python -m salubri_api.users add ... --password-stdin`.
Dans Docker : `docker compose exec api python -m salubri_api.users add ...`.
"""

import argparse
import getpass
import sys

from salubri_api.db import get_sessionmaker
from salubri_api.models import User
from salubri_api.models.audit import audit
from salubri_api.models.users import ROLES
from salubri_api.services.auth import hash_password


def _password(args: argparse.Namespace) -> str:
    if args.password_stdin:
        return sys.stdin.readline().rstrip("\n")
    p1 = getpass.getpass("Mot de passe (8 caractères minimum) : ")
    if getpass.getpass("Confirmer : ") != p1:
        sys.exit("Les deux mots de passe ne correspondent pas.")
    return p1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m salubri_api.users", description="Comptes de la mairie")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="créer un compte")
    a.add_argument("login")
    a.add_argument("--role", choices=ROLES, required=True)
    a.add_argument("--name", default=None, help="nom affiché (défaut : le login)")
    a.add_argument("--password-stdin", action="store_true")
    p = sub.add_parser("passwd", help="changer le mot de passe (ferme les sessions ouvertes)")
    p.add_argument("login")
    p.add_argument("--password-stdin", action="store_true")
    d = sub.add_parser("disable", help="désactiver un compte (ferme les sessions ouvertes)")
    d.add_argument("login")
    sub.add_parser("list", help="lister les comptes")
    args = ap.parse_args(argv)

    with get_sessionmaker()() as s:
        login = getattr(args, "login", "").strip().lower()
        user = s.query(User).filter(User.login == login).first() if login else None
        try:
            if args.cmd == "add":
                if user is not None:
                    sys.exit(f"Le compte « {login} » existe déjà.")
                u = User(
                    login=login,
                    display_name=args.name or login,
                    role=args.role,
                    password_hash=hash_password(_password(args)),
                )
                s.add(u)
                s.flush()
                audit(s, "create", "user", u.id, after={"login": login, "role": args.role}, actor="console")
                print(f"Compte « {login} » créé ({args.role}).")
            elif args.cmd == "list":
                for u in s.query(User).order_by(User.login):
                    print(f"{u.login:20} {u.role:11} {'actif' if u.active else 'désactivé':10} {u.display_name}")
            else:
                if user is None:
                    sys.exit(f"Compte « {login} » introuvable.")
                if args.cmd == "passwd":
                    user.password_hash = hash_password(_password(args))
                    action = "passwd"
                else:
                    user.active = False
                    action = "disable"
                user.session_version += 1
                audit(s, action, "user", user.id, after={"login": login}, actor="console")
                print(
                    f"Compte « {login} » : {'mot de passe changé' if action == 'passwd' else 'désactivé'}, sessions fermées."
                )
        except ValueError as exc:
            sys.exit(str(exc))
        s.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
