export interface GraphNode {
  uid: string
  labels: string[]
  properties: Record<string, any>
}

export interface GraphRelationship {
  type: string
  source_uid: string
  target_uid: string
  properties: Record<string, any>
}

export interface GraphPath {
  nodes: GraphNode[]
  relationships: GraphRelationship[]
}

export interface SubgraphResult {
  center_uid: string
  nodes: GraphNode[]
  relationships: GraphRelationship[]
  paths: GraphPath[]
}
