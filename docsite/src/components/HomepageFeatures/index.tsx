import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';
import Link from '@docusaurus/Link';

type FeatureItem = {
  title: string;
  description: ReactNode;
  link?: string;
  buttonText?: string;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Quick Start',
    description: (
      <>
        Get up and running with Intugle Data Tools in minutes.
      </>
    ),
    link: '/docs/intro',
    buttonText: 'Start Building →'
  },
  {
    title: 'Examples',
    description: (
      <>
        Real-world examples and use cases to inspire your projects.
      </>
    ),
    link: '/docs/intro',
    buttonText: 'View examples →'
  },
];

function Feature({title, description, link, buttonText}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className={clsx('card', styles.featureCard)}>
        <div className="card__header">
          <Heading as="h3">{title}</Heading>
        </div>
        <div className="card__body">
          <p className={styles.cardDescription}>{description}</p>
        </div>
        {link && (
          <div className={clsx('card__footer', styles.cardFooter)}>
            <Link
              className={clsx('button button--outline button--primary', styles.cardButton)}
              to={link}>
              {buttonText}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className={clsx('row', styles.featuresRow)}>
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
