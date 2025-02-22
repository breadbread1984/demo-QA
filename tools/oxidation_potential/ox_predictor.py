#!/usr/bin/python3

from os.path import join, abspath, dirname
from rdkit import Chem
import torch
from torch import load
import torch.nn.functional as F
from torch_geometric.data import Data, Batch
from .models import Predictor

class OxPredictor(object):
  def __init__(self, device = 'cpu'):
    assert device in {'cpu', 'cuda'}
    self.predictor = Predictor()
    script_path = abspath(__file__)
    script_dir = dirname(script_path)
    ckpt = load(join(script_dir, 'ckpt', 'model.pth'), map_location = torch.device('cpu'))['state_dict']
    ckpt = {(k if not k.startswith('module.') else k.replace('module.','')): v for k, v in ckpt.items()}
    self.predictor.load_state_dict(ckpt)
    self.predictor.eval().to(device)
    self.device = device
  def prepare_input(self, smiles: str):
    molecule = Chem.MolFromSmiles(smiles)
    nodes = list()
    edges = list()
    edges_type = list()
    for idx, atom in enumerate(molecule.GetAtoms()):
      assert idx == atom.GetIdx()
      nodes.append(atom.GetAtomicNum())
      for neighbor_atom in atom.GetNeighbors():
        neighbor_idx = neighbor_atom.GetIdx()
        bond = molecule.GetBondBetweenAtoms(idx, neighbor_idx)
        edges.append([idx, neighbor_idx])
        edges_type.append(bond.GetBondType())
    x = F.one_hot(torch.tensor(nodes, dtype = torch.long),118).to(torch.float32) # x.shape = (node_num, 118)
    edge_index = torch.tensor(edges, dtype = torch.long).t().contiguous() # edge_index.shape = (2, edge_num)
    edge_type = F.one_hot(torch.tensor(edges_type, dtype = torch.long),22).to(torch.float32) # edge_type.shape = (edge_num)
    data = Data(x = x, edge_index = edge_index, edge_type = edge_type)
    batch = Batch.from_data_list([data])
    return batch
  def predict(self, smiles: str):
    batch = self.prepare_input(smiles).to(self.device)
    ox = self.predictor(batch).detach().cpu().numpy() # ox.shape = (1,1)
    return ox

if __name__ == "__main__":
  ox_predictor = OxPredictor()
  print(ox_predictor.predictor('CCC(C#N)CC'))
