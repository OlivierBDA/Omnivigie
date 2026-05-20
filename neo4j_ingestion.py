import os
import json
import argparse
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "omnigraph")

def append_to_graph_model(label, pk_name, properties):
    """Met à jour le fichier graphModel.txt pour que le LLM connaisse ce nouveau noeud la prochaine fois."""
    model_path = "graphModel.txt"
    if not os.path.exists(model_path):
        return
        
    # Vérifier si le label existe déjà dans le modèle
    with open(model_path, "r", encoding="utf-8") as f:
        content = f.read()
        if f"({label})" in content:
            return # Déjà défini, on ne rajoute rien
            
    with open(model_path, "a", encoding="utf-8") as f:
        f.write(f"\n// ({label}) - [DYNAMIQUE] Nouveau concept métier identifié par le LLM.\n")
        f.write(f"// - {pk_name} (String) : Clé Primaire\n")
        for p in properties:
            f.write(f"// - {p['key']} (String) : Propriété ajoutée dynamiquement\n")
    print(f" -> [MAJ Modèle] Le nœud {label} a été ajouté dans graphModel.txt")

def ingest_graph(json_file_path):
    if not os.path.exists(json_file_path):
        print(f"Fichier introuvable : {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Connexion à la base Neo4j sur {URI}...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    try:
        with driver.session() as session:
            # 1. Ingestion du Document
            doc = data.get("document")
            if doc:
                print(f"Ingestion du Document : {doc['id']}")
                session.run(
                    "MERGE (d:Document {id: $id}) "
                    "ON CREATE SET d.title = $title, d.publish_date = date($date) "
                    "ON MATCH SET d.title = $title",
                    {"id": doc["id"], "title": doc["title"], "date": doc["publish_date"]}
                )

            # 2. Ingestion des entités statiques
            entity_mapping = {
                "organizations": ("Organization", "name", ["type"]),
                "models": ("Model", "name", ["version"]),
                "persons": ("Person", "name", ["role"]),
                "concepts": ("Concept", "name", ["domain"]),
                "geopolitical_entities": ("GeopoliticalEntity", "name", [])
            }

            for key, (label, id_field, props) in entity_mapping.items():
                items = data.get(key, [])
                for item in items:
                    item_id = item[id_field]
                    params = {"id": item_id}
                    
                    set_clause = ""
                    for p in props:
                        if p in item:
                            set_clause += f", n.{p} = ${p}"
                            params[p] = item[p]
                    
                    query = f"MERGE (n:{label} {{{id_field}: $id}})"
                    if set_clause:
                        query += f" ON CREATE SET {set_clause[2:]} ON MATCH SET {set_clause[2:]}"
                        
                    session.run(query, params)
                if items:
                    print(f"Ingéré {len(items)} {label}(s).")

            # 3. Ingestion des nouveaux noeuds proposés (Schéma dynamique)
            new_nodes = data.get("new_nodes_proposed", [])
            for node in new_nodes:
                label = node["proposed_label"]
                primary_key = node["primary_key"]
                
                # Ingestion dans Neo4j (totalement dynamique)
                params = {"id": primary_key}
                set_clauses = []
                props = node.get("properties", [])
                
                for i, prop in enumerate(props):
                    k = prop["key"]
                    v = prop["value"]
                    # Nettoyage du nom de la clé pour éviter les injections Cypher
                    safe_k = "".join(c for c in k if c.isalnum() or c == '_')
                    if safe_k:
                        set_clauses.append(f"n.{safe_k} = $p_{i}")
                        params[f"p_{i}"] = v
                
                query = f"MERGE (n:{label} {{name: $id}})" # On utilise 'name' par défaut pour coller au reste du modèle
                if set_clauses:
                    query += f" ON CREATE SET {', '.join(set_clauses)} ON MATCH SET {', '.join(set_clauses)}"
                
                session.run(query, params)
                
                # Mise à jour du fichier graphModel.txt
                append_to_graph_model(label, "name", props)
            
            if new_nodes:
                print(f"Ingéré {len(new_nodes)} nouveau(x) noeud(s) dynamique(s).")

            # 4. Ingestion des relations (Edges)
            edges = data.get("edges", [])
            for edge in edges:
                source_label = edge["source_label"]
                source_id = edge["source_id"]
                target_label = edge["target_label"]
                target_id = edge["target_id"]
                rel_type = edge["relation_type"]
                
                # Le nom de l'ID primaire dépend du label (Document utilise 'id', les autres utilisent 'name' par défaut)
                src_pk = "id" if source_label == "Document" else "name"
                tgt_pk = "id" if target_label == "Document" else "name"
                
                # Nettoyage du nom de relation (Cypher exige des caractères alphanumériques/underscores)
                safe_rel_type = "".join(c for c in rel_type if c.isalnum() or c == '_').upper()
                
                query = f"""
                MATCH (a:{source_label} {{{src_pk}: $src_id}}), (b:{target_label} {{{tgt_pk}: $tgt_id}})
                MERGE (a)-[r:{safe_rel_type}]->(b)
                """
                
                props = edge.get("properties", [])
                params = {"src_id": source_id, "tgt_id": target_id}
                
                if props:
                    set_clauses = []
                    for i, p in enumerate(props):
                        k = "".join(c for c in p["key"] if c.isalnum() or c == '_')
                        v = p["value"]
                        if k:
                            params[f"p_{i}"] = v
                            set_clauses.append(f"r.{k} = $p_{i}")
                    
                    if set_clauses:
                        query += f" ON CREATE SET {', '.join(set_clauses)} ON MATCH SET {', '.join(set_clauses)}"
                        
                session.run(query, params)
                
            print(f"Ingéré {len(edges)} relation(s).")
            print("Ingestion Neo4j terminée avec succès !")

    except Exception as e:
        print(f"Erreur lors de l'ingestion : {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingérer un JSON de Graph dans la base Neo4j.")
    parser.add_argument("json_file", help="Chemin vers le fichier JSON de la mindmap extrait en graphe")
    args = parser.parse_args()
    
    ingest_graph(args.json_file)
