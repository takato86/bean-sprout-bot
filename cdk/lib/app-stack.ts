import { Stack, StackProps, RemovalPolicy, CfnOutput, Duration } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Repository } from 'aws-cdk-lib/aws-ecr';
import { Role, ServicePrincipal, ManagedPolicy } from 'aws-cdk-lib/aws-iam';
import * as apprunner from '@aws-cdk/aws-apprunner-alpha';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';
import { Table, AttributeType } from 'aws-cdk-lib/aws-dynamodb';

interface AppStackProps extends StackProps {
  ecrRepository: Repository;
}

export class AppStack extends Stack {
  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props);

    // App Runnerのインスタンスロールを作成
    const instanceRole = new Role(this, 'InstanceRole', {
      assumedBy: new ServicePrincipal('tasks.apprunner.amazonaws.com'),
      roleName: 'HandsonAppRunnerInstanceRole',
    });

    instanceRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMReadOnlyAccess')
    );

    // App Runnerのサービスロールを作成
    const ecrAccessRole = new Role(this, 'EcrAccessRole', {
      assumedBy: new ServicePrincipal('build.apprunner.amazonaws.com'),
      roleName: 'HandsonAppRunnerECRAccessRole',
    });

    ecrAccessRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSAppRunnerServicePolicyForECRAccess')
    );

    const tableName = 'line-bot-hands-on-table';

    // App Runnerサービスを作成
    const apprunnerService = new apprunner.Service(this, 'AppRunnerService', {
      source: apprunner.Source.fromEcr({
        repository: props.ecrRepository,
        tagOrDigest: 'latest',
        imageConfiguration: {
          port: 8080,
          environmentSecrets: {
            CHANNEL_SECRET: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/CHANNEL_SECRET', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/CHANNEL_SECRET`)),
            CHANNEL_TOKEN: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/CHANNEL_TOKEN', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/CHANNEL_TOKEN`)),
            AWS_ACCESS_KEY_ID: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/AWS_ACCESS_KEY_ID', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/AWS_ACCESS_KEY_ID`)),
            AWS_SECRET_ACCESS_KEY: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/AWS_SECRET_ACCESS_KEY', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/AWS_SECRET_ACCESS_KEY`)),
            AZURE_OPENAI_API_KEY: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/AZURE_OPENAI_API_KEY', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/AZURE_OPENAI_API_KEY`)),
            AZURE_OPENAI_ENDPOINT: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/AZURE_OPENAI_ENDPOINT', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/AZURE_OPENAI_ENDPOINT`)),
            OPENAI_API_VERSION: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/OPENAI_API_VERSION', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/OPENAI_API_VERSION`)),
            OPEN_WEATHER_MAP_API_KEY: apprunner.Secret.fromSecretsManager(Secret.fromSecretPartialArn(this, 'linebot-apprunner-handson/OPEN_WEATHER_MAP_API_KEY', `arn:aws:ssm:ap-northeast-1:${this.account}:parameter/linebot-apprunner-handson/OPEN_WEATHER_MAP_API_KEY`)),
          },
          environmentVariables: {
            AWS_REGION: this.region,
            DYNAMODB_TABLE_NAME: tableName,
          }
        }
      }),
      accessRole: ecrAccessRole,
      instanceRole: instanceRole,
      serviceName: 'line-bot-hands-on',
      autoDeploymentsEnabled: true,
      healthCheck: apprunner.HealthCheck.http({
        path: '/health',
        healthyThreshold: 5,
        unhealthyThreshold: 10,
        interval: Duration.seconds(10),
        timeout: Duration.seconds(10),
      }),
    });

    // DynamoDBテーブルを作成
    const dynamodbTable = new Table(this, 'LineBotHandsonTable', {
      partitionKey: {
        name: 'publisherId',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: AttributeType.NUMBER,
      },
      removalPolicy: RemovalPolicy.DESTROY,
      tableName: tableName,
    });
    dynamodbTable.applyRemovalPolicy(RemovalPolicy.DESTROY);

    // App RunnerのインスタンスロールにDynamoDBテーブルへのアクセス権限を付与
    dynamodbTable.grantReadWriteData(instanceRole);

    new CfnOutput(this, 'AppRunnerServiceUrl', {
      value: `https://${apprunnerService.serviceUrl}`,
    });
  }
}
