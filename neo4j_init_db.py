import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "omnigraph")

def create_constraints(tx):
    # Les contraintes d'unicité (PRIMARY KEY équivalent) dans Neo4j
    constraints = [
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT organization_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT model_name IF NOT EXISTS FOR (m:Model) REQUIRE m.name IS UNIQUE",
        "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT geo_name IF NOT EXISTS FOR (g:GeopoliticalEntity) REQUIRE g.name IS UNIQUE"
    ]
    for q in constraints:
        tx.run(q)

def init_db():
    print(f"Connexion à Neo4j sur {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    try:
        with driver.session() as session:
            session.execute_write(create_constraints)
        print("Les contraintes d'unicité ont été créées avec succès dans Neo4j.")
    except Exception as e:
        print(f"Erreur lors de la création des contraintes : {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    init_db()
