import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import List, Tuple
import os
import time

from nnue_torch import NNUEPyTorch
from selfplay import SelfPlayData, states_to_tensors


class NNUEDataset(Dataset):
    """NNUE 训练数据集"""
    def __init__(self, features, targets):
        self.features = features
        self.targets = targets
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]


class NNUETrainer:
    """
    NNUE 训练器。
    使用 MSE 损失函数训练网络预测局面胜率。
    """
    def __init__(
        self,
        model: NNUEPyTorch,
        lr: float = 0.001,
        weight_decay: float = 1e-5,
        device: str = 'auto'
    ):
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        self.model = model.to(self.device)
        self.optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
        self.criterion = nn.MSELoss()
        
    def train_epoch(self, dataloader: DataLoader) -> float:
        """训练一个 epoch，返回平均损失"""
        self.model.train()
        total_loss = 0
        num_batches = 0

        for features, targets in dataloader:
            features = features.to(self.device)
            targets = targets.to(self.device)

            self.optimizer.zero_grad()

            # 使用 forward_from_features 进行完整前向传播，训练两层权重
            outputs = self.model.forward_from_features(features)
            loss = self.criterion(outputs, targets)

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        return total_loss / num_batches if num_batches > 0 else 0.0

    def evaluate(self, dataloader: DataLoader) -> float:
        """在验证集上评估，返回平均损失"""
        self.model.eval()
        total_loss = 0
        num_batches = 0

        with torch.no_grad():
            for features, targets in dataloader:
                features = features.to(self.device)
                targets = targets.to(self.device)

                outputs = self.model.forward_from_features(features)
                loss = self.criterion(outputs, targets)

                total_loss += loss.item()
                num_batches += 1

        return total_loss / num_batches if num_batches > 0 else 0.0
    
    def train(
        self,
        train_dataset: List[SelfPlayData],
        val_dataset: List[SelfPlayData] = None,
        epochs: int = 10,
        batch_size: int = 64,
        shuffle: bool = True,
        verbose: bool = True,
        lmbda: float = 0.75
    ) -> dict:
        """
        完整训练流程。

        Args:
            train_dataset: 训练数据
            val_dataset: 验证数据（可选）
            epochs: 训练轮数
            batch_size: 批大小
            shuffle: 是否打乱数据
            verbose: 是否打印训练过程
            lmbda: 混合目标权重，target = λ*search_score + (1-λ)*game_result

        Returns:
            dict: 训练历史记录
        """
        train_features, train_targets = states_to_tensors(train_dataset, self.model, lmbda=lmbda)
        print(f"Training data: {len(train_features)} samples")
        
        train_dataset_t = NNUEDataset(train_features, train_targets)
        train_loader = DataLoader(train_dataset_t, batch_size=batch_size, shuffle=shuffle)
        
        val_loader = None
        if val_dataset is not None:
            val_features, val_targets = states_to_tensors(val_dataset, self.model, lmbda=lmbda)
            print(f"Validation data: {len(val_features)} samples")
            val_dataset_t = NNUEDataset(val_features, val_targets)
            val_loader = DataLoader(val_dataset_t, batch_size=batch_size, shuffle=False)
        
        history = {
            'train_loss': [],
            'val_loss': [],
            'epochs': epochs
        }
        
        start_time = time.time()
        
        for epoch in range(epochs):
            epoch_start = time.time()
            
            train_loss = self.train_epoch(train_loader)
            history['train_loss'].append(train_loss)
            
            val_loss = None
            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                history['val_loss'].append(val_loss)
            
            epoch_time = time.time() - epoch_start
            
            if verbose:
                if val_loss is not None:
                    print(f"Epoch {epoch+1}/{epochs} | "
                          f"Train Loss: {train_loss:.4f} | "
                          f"Val Loss: {val_loss:.4f} | "
                          f"Time: {epoch_time:.2f}s")
                else:
                    print(f"Epoch {epoch+1}/{epochs} | "
                          f"Train Loss: {train_loss:.4f} | "
                          f"Time: {epoch_time:.2f}s")
        
        total_time = time.time() - start_time
        if verbose:
            print(f"\nTraining completed in {total_time:.2f}s")
        
        return history
    
    def save_model(self, filepath: str):
        """保存模型"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_config': {
                'input_size': self.model.input_size,
                'hidden_size': self.model.hidden_size
            }
        }, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """加载模型"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        print(f"Model loaded from {filepath}")


class IncrementalTrainer(NNUETrainer):
    """
    增量训练器：用于迭代训练。
    每次用新的自我对弈数据微调已有模型。
    """
    def __init__(self, model: NNUEPyTorch, lr: float = 0.0005, **kwargs):
        super().__init__(model, lr=lr, **kwargs)
    
    def train_with_incremental_data(
        self,
        new_data: List[SelfPlayData],
        old_data: List[SelfPlayData] = None,
        epochs: int = 5,
        batch_size: int = 64,
        verbose: bool = True,
        lmbda: float = 0.75
    ) -> dict:
        """
        使用新增数据训练，可选择保留部分旧数据。
        """
        combined_data = new_data.copy()
        if old_data is not None:
            sample_size = min(len(old_data), len(new_data))
            combined_data.extend(old_data[:sample_size])

        if verbose:
            print(f"Combined training data: {len(combined_data)} games")

        return self.train(
            train_dataset=combined_data,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            lmbda=lmbda
        )


def transfer_from_simple_nnue(simple_nnue, torch_nnue):
    """
    从简单 NNUE (nnue.py) 迁移权重到 PyTorch 版本。
    """
    for i in range(torch_nnue.input_size):
        for j in range(torch_nnue.hidden_size):
            torch_nnue.feature_weights.data[i, j] = simple_nnue.feature_weights[i][j]
    
    for j in range(torch_nnue.hidden_size):
        torch_nnue.feature_biases.data[j] = simple_nnue.feature_biases[j]
        torch_nnue.output_weights.data[j] = simple_nnue.output_weights[j]
    
    torch_nnue.output_bias.data[0] = simple_nnue.output_bias
    
    return torch_nnue


if __name__ == "__main__":
    from envs.tictactoe import TicTacToe
    from nnue_torch import NNUEPyTorch
    from selfplay import SelfPlayManager
    
    print("=" * 50)
    print("Testing Training with TicTacToe")
    print("=" * 50)
    
    game = TicTacToe()
    nnue = NNUEPyTorch(input_size=18, hidden_size=32)
    manager = SelfPlayManager(game, nnue)
    
    print("\nGenerating training data...")
    dataset = manager.generate_dataset(num_games=50)
    
    print("\nTraining...")
    trainer = NNUETrainer(nnue, lr=0.01)
    history = trainer.train(dataset, epochs=10, verbose=True)
    
    print("\nSaving model...")
    trainer.save_model('models/nnue_tictactoe.pt')
