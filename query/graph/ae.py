import random
import torch
import torch.nn as nn
import torch.nn.functional as F


class Residual(nn.Module):
    def __init__(self, in_channels, num_hiddens, num_residual_hiddens):
        super(Residual, self).__init__()
        self._block = nn.Sequential(
            nn.ReLU(True),
            nn.Conv2d(in_channels=in_channels,
                      out_channels=num_residual_hiddens,
                      kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(num_residual_hiddens),
            nn.ReLU(True),
            nn.Conv2d(in_channels=num_residual_hiddens,
                      out_channels=num_hiddens,
                      kernel_size=1, stride=1, bias=False)
        )

    def forward(self, x):
        return x + self._block(x)


class ResidualStack(nn.Module):
    def __init__(self, in_channels, num_hiddens, num_residual_layers, num_residual_hiddens):
        super(ResidualStack, self).__init__()
        self._num_residual_layers = num_residual_layers
        self._layers = nn.ModuleList([Residual(in_channels, num_hiddens, num_residual_hiddens)
                                      for _ in range(self._num_residual_layers)])

    def forward(self, x):
        for i in range(self._num_residual_layers):
            x = self._layers[i](x)
        return x


class Encoder(nn.Module):
    def __init__(self, in_channels, num_hiddens, num_residual_layers, num_residual_hiddens):
        super(Encoder, self).__init__()

        self._conv_1 = nn.Conv2d(in_channels=in_channels,
                                 out_channels=num_hiddens // 4,
                                 kernel_size=4,
                                 stride=2, padding=1)
        self._conv_2 = nn.Conv2d(in_channels=num_hiddens // 4,
                                 out_channels=num_hiddens // 2,
                                 kernel_size=4,
                                 stride=2, padding=1)

        self._conv_3 = nn.Conv2d(in_channels=num_hiddens // 2,
                                 out_channels=num_hiddens // 2,
                                 kernel_size=3,
                                 stride=1, padding=1)

        self._conv_4 = nn.Conv2d(in_channels=num_hiddens // 2,
                                 out_channels=num_hiddens,
                                 kernel_size=4,
                                 stride=2, padding=1)
        self._conv_5 = nn.Conv2d(in_channels=num_hiddens,
                                 out_channels=num_hiddens,
                                 kernel_size=3,
                                 stride=1, padding=1)

        self._residual_stack_1 = ResidualStack(in_channels=num_hiddens // 2,
                                               num_hiddens=num_hiddens // 2,
                                               num_residual_layers=num_residual_layers,
                                               num_residual_hiddens=num_residual_hiddens)
        self._residual_stack_2 = ResidualStack(in_channels=num_hiddens,
                                               num_hiddens=num_hiddens,
                                               num_residual_layers=num_residual_layers,
                                               num_residual_hiddens=num_residual_hiddens)

        self.batch_norm1 = nn.BatchNorm2d(num_hiddens // 4)
        self.batch_norm2 = nn.BatchNorm2d(num_hiddens // 2)
        self.batch_norm3 = nn.BatchNorm2d(num_hiddens // 2)
        self.batch_norm4 = nn.BatchNorm2d(num_hiddens // 2)
        self.batch_norm5 = nn.BatchNorm2d(num_hiddens)
        self.batch_norm6 = nn.BatchNorm2d(num_hiddens)
        self.batch_norm7 = nn.BatchNorm2d(num_hiddens)

        self.relu = nn.ReLU(inplace=True)
        self.avg_pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, inputs):
        x = self._conv_1(inputs)
        x = self.batch_norm1(x)
        x = self.relu(x)    # 16 x 16

        x = self._conv_2(x)
        x = self.batch_norm2(x)
        x = self.relu(x)    # 8 x 8

        x = self._conv_3(x)
        x = self.batch_norm3(x) # 8 x 8

        x = self._residual_stack_1(x)
        x = self.batch_norm4(x)
        x = self.relu(x)

        x = self._conv_4(x)
        x = self.batch_norm5(x)
        x = self.relu(x)  # 4 x 4

        x = self._conv_5(x)
        x = self.batch_norm6(x)  # 4 x 4

        x = self._residual_stack_2(x)
        x = self.batch_norm7(x)

        return self.avg_pool(x)


class Decoder(nn.Module):
    def __init__(self, in_channels, num_residual_layers, num_residual_hiddens):
        super(Decoder, self).__init__()

        self._residual_stack1 = ResidualStack(in_channels=in_channels // 2,
                                              num_hiddens=in_channels // 2,
                                              num_residual_layers=num_residual_layers,
                                              num_residual_hiddens=num_residual_hiddens)

        self._residual_stack2 = ResidualStack(in_channels=in_channels // 8,
                                              num_hiddens=in_channels // 8,
                                              num_residual_layers=num_residual_layers,
                                              num_residual_hiddens=num_residual_hiddens)

        self._conv_trans_1 = nn.ConvTranspose2d(in_channels=in_channels,
                                                out_channels=in_channels // 2,
                                                kernel_size=4,
                                                stride=4)

        self._conv_trans_2 = nn.ConvTranspose2d(in_channels=in_channels // 2,
                                                out_channels=in_channels // 4,
                                                kernel_size=4,
                                                stride=2, padding=1)

        self._conv_trans_3 = nn.ConvTranspose2d(in_channels=in_channels // 4,
                                                out_channels=in_channels // 8,
                                                kernel_size=4,
                                                stride=2, padding=1)

        self._conv_trans_4 = nn.ConvTranspose2d(in_channels=in_channels // 8,
                                                out_channels=3,
                                                kernel_size=4,
                                                stride=2, padding=1)

        self.batch_norm1 = nn.BatchNorm2d(in_channels // 2)
        self.batch_norm2 = nn.BatchNorm2d(in_channels // 2)
        self.batch_norm3 = nn.BatchNorm2d(in_channels // 4)
        self.batch_norm4 = nn.BatchNorm2d(in_channels // 8)
        self.batch_norm5 = nn.BatchNorm2d(in_channels // 8)

        self.relu = nn.ReLU(inplace=True)

    def forward(self, inputs):
        x = self._conv_trans_1(inputs)
        x = self.batch_norm1(x)

        x = self._residual_stack1(x)
        x = self.batch_norm2(x)
        x = self.relu(x)

        x = self._conv_trans_2(x)
        x = self.batch_norm3(x)
        x = self.relu(x)

        x = self._conv_trans_3(x)
        x = self.batch_norm4(x)

        x = self._residual_stack2(x)
        x = self.batch_norm5(x)
        x = self.relu(x)

        return self._conv_trans_4(x)


class AE(nn.Module):
    def __init__(self, num_residual_layers, num_residual_hiddens, embedding_dim):
        super(AE, self).__init__()

        self.embedding_dim = embedding_dim

        self._encoder = Encoder(3, embedding_dim,
                                num_residual_layers,
                                num_residual_hiddens)
        self._decoder = Decoder(embedding_dim,
                                num_residual_layers,
                                num_residual_hiddens)

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        encoder_out = self.relu(self._encoder(x))
        x_recon = self._decoder(encoder_out)

        return x_recon, encoder_out
