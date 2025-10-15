#!/usr/bin/env python3
"""
Generic script to extract system variable hierarchy from TTL ontology files using SPARQL.
Works with FMU, SSP, and other ontology patterns.
"""

from rdflib import Graph, Namespace
import sys
from pathlib import Path

def extract_hierarchy(ttl_file_path):
    """
    Extract the hierarchy of systems and their variables from a TTL file.
    Handles multiple ontology patterns (FMU, SSP, etc.)
    
    Args:
        ttl_file_path: Path to the TTL file
    
    Returns:
        List of hierarchical variable strings
    """
    # Create a graph and parse the TTL file
    g = Graph()
    g.parse(ttl_file_path, format='turtle')
    
    # Generic SPARQL query that works across different ontology patterns
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ssn: <http://www.w3.org/ns/ssn/>
    PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX fmu: <http://example.com/fmu#>
    PREFIX ssp: <http://example.com/ssp#>
    
    SELECT DISTINCT ?system ?systemLabel ?property ?propertyLabel ?variableName
    WHERE {
        # Find systems (can be FMU, SSP Component, or other System types)
        {
            ?system a fmu:FMU .
        } UNION {
            ?system a ssp:Component .
        } UNION {
            ?system a ssp:System .
        } UNION {
            ?system a ssn:System .
        }
        
        # Get system label
        OPTIONAL { ?system rdfs:label ?systemLabel }
        
        # Find properties/variables of the system
        {
            # Properties linked via ssn:isPropertyOf
            ?property ssn:isPropertyOf ?system .
        } UNION {
            # Variables linked via fmu:hasVariable
            ?system fmu:hasVariable ?property .
        } UNION {
            # Variables linked via ssp:hasVariable
            ?system ssp:hasVariable ?property .
        }
        
        # Get property label
        OPTIONAL { ?property rdfs:label ?propertyLabel }
        
        # Get variable names (different predicates)
        OPTIONAL { 
            { ?property fmu:hasFMUVariableName ?variableName }
            UNION
            { ?property ssp:hasVariableName ?variableName }
        }
    }
    ORDER BY ?systemLabel ?propertyLabel
    """
    
    # Execute the query
    results = g.query(query)
    
    # Process results
    hierarchy = []
    seen = set()  # To avoid duplicates
    
    for row in results:
        # Get system name
        if row.systemLabel:
            system_name = str(row.systemLabel)
        else:
            # Extract local name from URI
            system_name = str(row.system).split('#')[-1].split('/')[-1]
        
        # Get property/variable name - always use the URI local name
        # Extract local name from URI (e.g., "Power" from "fmu:Power")
        prop_name = str(row.property).split('#')[-1].split('/')[-1]
        
        # Create hierarchy entry
        hierarchy_entry = f"{system_name}.{prop_name}"
        
        # Avoid duplicates
        if hierarchy_entry not in seen:
            seen.add(hierarchy_entry)
            hierarchy.append(hierarchy_entry)
    
    return sorted(hierarchy)

def process_multiple_files(file_paths):
    """
    Process multiple TTL files and extract hierarchies.
    
    Args:
        file_paths: List of file paths to process
    
    Returns:
        Dictionary mapping file names to their hierarchies
    """
    results = {}
    
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            try:
                hierarchy = extract_hierarchy(file_path)
                results[path.name] = hierarchy
            except Exception as e:
                print(f"Error processing {path.name}: {e}")
                results[path.name] = []
        else:
            print(f"File not found: {file_path}")
            results[path.name] = []
    
    return results

def main():
    """Main function to run the script."""
    
    if len(sys.argv) < 2:
        print("Usage: python script.py <ttl_file> [ttl_file2 ...]")
        print("\nExample:")
        print("  python script.py engine.ttl")
        print("  python script.py engine.ttl hull.ttl propeller.ttl ship.ttl")
        sys.exit(1)
    
    file_paths = sys.argv[1:]
    
    try:
        if len(file_paths) == 1:
            # Single file processing
            print(f"Extracting hierarchy from: {file_paths[0]}")
            print("-" * 50)
            
            hierarchy = extract_hierarchy(file_paths[0])
            
            if hierarchy:
                for entry in hierarchy:
                    print(entry)
                print("-" * 50)
                print(f"Total variables found: {len(hierarchy)}")
            else:
                print("No variables found in the file.")
        else:
            # Multiple files processing
            print("Processing multiple files...")
            print("=" * 50)
            
            results = process_multiple_files(file_paths)
            
            for filename, hierarchy in results.items():
                print(f"\n{filename}:")
                print("-" * 50)
                if hierarchy:
                    for entry in hierarchy:
                        print(f"  {entry}")
                    print(f"  Total: {len(hierarchy)} variables")
                else:
                    print("  No variables found")
            
            print("=" * 50)
            total = sum(len(h) for h in results.values())
            print(f"Total variables across all files: {total}")
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file(s): {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()